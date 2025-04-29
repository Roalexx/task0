import json
from app.celery_app import celery, redis_conn



@celery.task(bind=True, name= "tasks.reverse_text")
def reverse_text(self, text):
     result = text[::-1]
     redis_conn.hset("task_results", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result

@celery.task(bind=True, name="tasks.uppercase")
def uppercase(self, text):
     result = text.upper()
     redis_conn.hset("task_results", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result

@celery.task(bind=True, name="tasks.sum_numbers")
def sum_numbers(self, numbers):
     result = sum(map(int, numbers.split("+")))
     redis_conn.hset("task_result", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result