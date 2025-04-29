from flask import Flask, request, jsonify
from app import create_app
from flasgger import Swagger
from app.tasks import sum_numbers, uppercase, reverse_text
from app.async_db_tasks import create_user, list_users, create_asset, list_assets
from config import DATABASE_URL
from app.celery_app import celery, redis_conn
from models.db import db
import pika
import json

app = create_app()

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

swagger = Swagger(app)

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
        description: Input data to process
      - name: task_type
        in: formData
        type: string
        required: true
        description: Type of task (reverse_text, uppercase, sum_numbers)
    responses:
      202:
        description: Task created and queued successfully
    """
    data = request.form['data']
    task_type = request.form['task_type']
    task = task_map[task_type].delay(data)
    return jsonify({
        "task_id": task.id,
        "status": "queued"
    }), 202

@app.route('/results/<task_id>', methods=["GET"])
def get_results(task_id):
    """
    Get result of a specific task
    ---
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: ID of the task
    responses:
      202:
        description: Task result retrieved successfully
    """
    result = celery.AsyncResult(task_id)
    return jsonify({
        "task_id": task_id,
        "status": result.state,
        "result": result.result
    }), 202

@app.route('/results', methods=["GET"])
def get_all_results():
    """
    Get all task results
    ---
    responses:
      202:
        description: List of all completed tasks
    """
    all_data = redis_conn.hgetall("task_results")
    completed = []

    for task_id_byte, data_byte in all_data.items():
        task_id = task_id_byte.decode()
        data = json.loads(data_byte.decode())
        async_result = celery.AsyncResult(task_id)

        completed.append({
            "task_id": task_id,
            "status": async_result.status,
            "result": async_result.result if async_result.successful() else None
        })

    return jsonify(completed), 202

@app.route('/queue', methods=["GET"])
def get_queue():
    """
    Get queued tasks from RabbitMQ
    ---
    responses:
      202:
        description: List of tasks currently queued
      500:
        description: Error while fetching tasks
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()

        method_frame, header_frame, body = channel.basic_get(queue='celery')
        tasks = []

        while method_frame:
            task = body.decode()
            tasks.append(task)
            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)
            method_frame, header_frame, body = channel.basic_get(queue='celery')

        connection.close()

        return jsonify({"queued_tasks": tasks}), 202
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
      202:
        description: User creation task queued successfully
    """
    username = request.form['username']
    email = request.form['email']
    task = create_user.delay(username, email)
    result = task.get()
    return jsonify({
        "task_id": task.id,
        "status": "queued",
        "result": result
    }), 202

@app.route('/get_users', methods=["GET"])
def get_users():
    """
    Get list of users
    ---
    responses:
      200:
        description: List of all users
    """
    task = list_users.delay()
    result = task.get() 
    return jsonify({
        "task_id": task.id,
        "status": "queued",
        "result": result
    }), 200

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
        description: Asset name
      - name: value
        in: formData
        type: number
        required: true
        description: Asset value
      - name: user_id
        in: formData
        type: integer
        required: true
        description: Owner user ID
    responses:
      200:
        description: Asset created successfully
    """
    name = request.form['name']
    value = float(request.form['value'])
    user_id = int(request.form['user_id'])
    task = create_asset.delay(name, value, user_id)
    result = task.get()
    return jsonify({
        "task_id": task.id,
        "status": "queued",
        "result": result
    }), 200

@app.route('/get_asset', methods=["GET"])
def get_asset():
    """
    Get list of assets
    ---
    responses:
      200:
        description: List of all assets
    """
    task = list_assets.delay()    
    result = task.get() 
    return jsonify({
        "task_id": task.id,
        "status": "queued",
        "result": result
    }), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
