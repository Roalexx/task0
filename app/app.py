from flask import Flask , request, jsonify
from flasgger import Swagger
from tasks import sum_numbers, uppercase, reverse_text
from sync_tasks import create_asset, create_user, list_assets, list_users
from config import DATABASE_URL
from models.db import db
from models.user import User
from models.asset import Asset
import redis
import pika
import base64
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
swagger = Swagger(app)
redis_conn = redis.Redis(host="redis", port=6379, db=0)


task_map = {
    "reverse_text": reverse_text,
    "uppercase": uppercase,
    "sum_numbers": sum_numbers
}

@app.route("/tasks", methods=["POST"])
def create_task():
    """
    Create a new task
    ---
    parameters:
      - name: data
        in: formData
        type: string
        required: true
        description: Input data to be processed
      - name: task_type
        in: formData
        type: string
        required: true
        description: Task type to execute (reverse_text, uppercase, sum_numbers)
    responses:
      202:
        description: Task has been queued successfully
    """
    data = request.form['data']
    task_type = request.form['task_type']
    result = task_map[task_type].delay(data)
    return jsonify({
        "task_id": result.id,
        "status": "queued"
    }), 202

@app.route('/results/<task_id>', methods=["GET"])
def get_results(task_id):
    """
    Get the result of a specific task
    ---
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: The ID of the task to retrieve
    responses:
      200:
        description: Task result retrieved successfully
    """
    from tasks import app as celery_app
    result = celery_app.AsyncResult(task_id)
    return jsonify({
        "task_id": task_id,
        "status": result.state,
        "result": result.result
    }), 202


@app.route('/results', methods=["GET"])
def get_all_results():
    """
    Get all completed task results
    ---
    responses:
      200:
        description: List of all completed tasks
    """
    from tasks import app as celery_app
    all_data = redis_conn.hgetall("task_results")
    completed = []

    for task_id_byte, data_byte in all_data.items():
        task_id = task_id_byte.decode()
        data = json.loads(data_byte.decode())
        async_result = celery_app.AsyncResult(task_id)

        completed.append({
            "task_id": task_id,
            "status": async_result.status,
            "result": async_result.result if async_result.successful() else None
        })

    return jsonify(completed), 202


@app.route('/queue', methods=["GET"])
def get_queue():
    """
    Get current queued tasks from RabbitMQ
    ---
    responses:
      200:
        description: List of tasks currently queued
      500:
        description: Error while fetching queue from RabbitMQ
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq')
        )
        channel = connection.channel()

        method_frame, header_frame, body = channel.basic_get(queue='celery')

        tasks = []

        while method_frame:
            task = body.decode()
            tasks.append(task)

            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)
            method_frame, header_frame, body = channel.basic_get(queue='celery')

        connection.close()

        return jsonify({"queued tasks": tasks}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/add_user', methods=["POST"])
def add_user():
    """
    Add a new user
    ---
    parameters:
      - name: username
        in: formData
        type: string
        required: true
        description: Username of the new user
      - name: email
        in: formData
        type: string
        required: true
        description: Email of the new user
    responses:
      200:
        description: User created successfully
        schema:
          id: CreateUserResponse
          properties:
            message:
              type: string
            user_id:
              type: integer
    """
    username = request.form['username']
    email = request.form['email']
    result = create_user(username,email)
    return jsonify(result)

@app.route('/get_users', methods=["GET"])
def get_users():
    """
    List all users
    ---
    responses:
      200:
        description: A list of all users
        schema:
          type: array
          items:
            properties:
              id:
                type: integer
              username:
                type: string
              email:
                type: string
    """
    result = list_users()
    return jsonify(result)

@app.route('/add_asset', methods=["POST"])
def add_asset():
    """
    Add a new asset
    ---
    parameters:
      - name: name
        in: formData
        type: string
        required: true
        description: Name of the asset
      - name: value
        in: formData
        type: number
        required: true
        description: Value of the asset
      - name: user_id
        in: formData
        type: integer
        required: true
        description: ID of the user who owns the asset
    responses:
      200:
        description: Asset created successfully
        schema:
          id: CreateAssetResponse
          properties:
            message:
              type: string
            asset_id:
              type: integer
    """
    name = request.form['name']
    value = float(request.form['value'])
    user_id = int(request.form['user_id'])
    result = create_asset(name, value, user_id)
    return jsonify(result)

@app.route('/get_asset', methods=["GET"])
def get_asset():
    """
    List all assets
    ---
    responses:
      200:
        description: A list of all assets
        schema:
          type: array
          items:
            properties:
              id:
                type: integer
              name:
                type: string
              value:
                type: number
              owner_username:
                type: string
    """
    result = list_assets()
    return jsonify(result)

db.init_app(app)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)