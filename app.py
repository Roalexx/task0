from flask import Flask, request, jsonify
from app import create_app
from flasgger import Swagger, swag_from
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
@swag_from({
    'tags': ['With Redis'],
    'summary': 'Create a new task',
    'description': 'Creates an asynchronous task of type: reverse_text, uppercase, or sum_numbers.',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'data',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Input data to process'
        },
        {
            'name': 'task_type',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Type of task (reverse_text, uppercase, sum_numbers)'
        }
    ],
    'responses': {
        202: {
            'description': 'Task created and queued successfully',
            'examples': {
                'application/json': {
                    'task_id': 'abc123',
                    'status': 'queued'
                }
            }
        },
        400: {
            'description': 'Bad request (missing or invalid parameters)'
        }
    }
})
def create_task():    
    data = request.form['data']
    task_type = request.form['task_type']
    task = task_map[task_type].delay(data)
    return jsonify({
        "task_id": task.id,
        "status": "queued"
    }), 202

@app.route('/results/<task_id>', methods=["GET"])
@swag_from({
    'tags': ['With Redis'],
    'summary': 'Get task result',
    'description': 'Retrieves the current status and result of a previously submitted asynchronous task using its task_id.',
    'parameters': [
        {
            'name': 'task_id',
            'in': 'query',
            'type': 'string',
            'required': True,
            'description': 'ID of the task to retrieve status for'
        }
    ],
    'responses': {
        202: {
            'description': 'Task status and result returned',
            'examples': {
                'application/json': {
                    'task_id': 'abc123',
                    'status': 'SUCCESS',
                    'result': 'HELLO'
                }
            }
        },
        404: {
            'description': 'Task not found or expired'
        }
    }
})
def get_results(task_id):
    result = celery.AsyncResult(task_id)
    return jsonify({
        "task_id": task_id,
        "status": result.state,
        "result": result.result
    }), 202

@app.route('/results', methods=["GET"])
@swag_from({
    'tags': ['With Redis'],
    'summary': 'Get all task results',
    'description': 'Returns a list of all previously submitted tasks, their current statuses, and results if available.',
    'responses': {
        202: {
            'description': 'List of task results returned successfully',
            'examples': {
                'application/json': [
                    {
                        'task_id': 'abc123',
                        'status': 'SUCCESS',
                        'result': 'HELLO'
                    },
                    {
                        'task_id': 'xyz456',
                        'status': 'FAILURE',
                        'result': None
                    }
                ]
            }
        }
    }
})
def get_all_results():
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
@swag_from({
    'tags': ['With Redis'],
    'summary': 'Get pending Celery tasks from RabbitMQ',
    'description': 'Fetches all unprocessed (queued) tasks currently sitting in the RabbitMQ "celery" queue. '
                   'This endpoint directly accesses RabbitMQ and does not rely on Celery result backend.',
    'responses': {
        202: {
            'description': 'Successfully retrieved queued tasks',
            'examples': {
                'application/json': {
                    'queued_tasks': [
                        '{"id": "123", "task": "reverse_text", "args": ["hello"]}',
                        '{"id": "456", "task": "uppercase", "args": ["world"]}'
                    ]
                }
            }
        },
        500: {
            'description': 'Internal server error, usually connection or decoding issue',
            'examples': {
                'application/json': {
                    'error': 'Connection refused'
                }
            }
        }
    }
})
def get_queue():
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
@swag_from({
    'tags': ['Users'],
    'summary': 'Create a new user (async)',
    'description': 'Creates a new user using Celery. Accepts username and email as form-data, returns task ID and result.',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'username',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Username for the new user'
        },
        {
            'name': 'email',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Email address of the new user'
        }
    ],
    'responses': {
        202: {
            'description': 'User creation task queued and result returned',
            'examples': {
                'application/json': {
                    'task_id': '123abc',
                    'status': 'queued',
                    'result': {
                        'message': 'User johndoe created successfully',
                        'user_id': 12
                    }
                }
            }
        },
        400: {
            'description': 'Missing or invalid parameters'
        }
    }
})
def add_user():
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
@swag_from({
    'tags': ['Users'],
    'summary': 'List all users (async)',
    'description': 'Fetches all users via a Celery task. Returns a message and list of users with their ID, username, and email.',
    'responses': {
        200: {
            'description': 'List of users fetched successfully',
            'examples': {
                'application/json': {
                    'task_id': 'abc123',
                    'status': 'queued',
                    'result': {
                        'message': 'Users fetched successfully',
                        'users': [
                            {
                                'id': 1,
                                'username': 'johndoe',
                                'email': 'john@example.com'
                            },
                            {
                                'id': 2,
                                'username': 'janedoe',
                                'email': 'jane@example.com'
                            }
                        ]
                    }
                }
            }
        },
        500: {
            'description': 'Error fetching users from database'
        }
    }
})
def get_users():
    task = list_users.delay()
    result = task.get() 
    return jsonify({
        "task_id": task.id,
        "status": "queued",
        "result": result
    }), 200

@app.route('/add_asset', methods=["POST"])
@swag_from({
    'tags': ['Assets'],
    'summary': 'Create a new asset (async)',
    'description': 'Creates a new asset using Celery. Accepts asset name, value, and user_id as form-data.',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'name',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Name of the asset (e.g., Laptop, Phone)'
        },
        {
            'name': 'value',
            'in': 'formData',
            'type': 'number',
            'required': True,
            'description': 'Monetary value of the asset'
        },
        {
            'name': 'user_id',
            'in': 'formData',
            'type': 'integer',
            'required': True,
            'description': 'User ID who owns the asset'
        }
    ],
    'responses': {
        200: {
            'description': 'Asset created successfully',
            'examples': {
                'application/json': {
                    'task_id': 'xyz789',
                    'status': 'queued',
                    'result': {
                        'message': 'Asset Laptop created successfully',
                        'asset_id': 5
                    }
                }
            }
        },
        400: {
            'description': 'Missing or invalid parameters'
        }
    }
})
def add_asset():
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
@swag_from({
    'tags': ['Assets'],
    'summary': 'List all assets (async)',
    'description': 'Fetches all assets via a Celery task. Each asset includes its ID, name, value, and owner information.',
    'responses': {
        200: {
            'description': 'List of assets fetched successfully',
            'examples': {
                'application/json': {
                    'task_id': 'abc987',
                    'status': 'queued',
                    'result': [
                        {
                            'id': 1,
                            'name': 'Laptop',
                            'value': 3000.0,
                            'owner': {
                                'user_id': 7,
                                'username': 'johndoe'
                            }
                        },
                        {
                            'id': 2,
                            'name': 'Phone',
                            'value': 1500.0,
                            'owner': {
                                'user_id': 8,
                                'username': 'janedoe'
                            }
                        }
                    ]
                }
            }
        },
        500: {
            'description': 'Failed to fetch assets'
        }
    }
})
def get_asset():
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
