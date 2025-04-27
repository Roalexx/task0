import redis
import json
from celery import Celery

app = Celery("task")

app.config_from_object("celeryconfig")

redis_conn =  redis.Redis(host="redis", port=6379, db=0)

@app.task(bind=True, name= "tasks.reverse_text")
def reverse_text(self, text):
     result = text[::-1]
     redis_conn.hset("task_results", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result

@app.task(bind=True, name="tasks.uppercase")
def uppercase(self, text):
     result = text.upper()
     redis_conn.hset("task_results", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result

@app.task(bind=True, name="tasks.sum_numbers")
def sum_numbers(self, numbers):
     result = sum(map(int, numbers.split("+")))
     redis_conn.hset("task_result", self.request.id, json.dumps({
          "task_id": self.request.id,
          "status": "queued"
     }))
     return result