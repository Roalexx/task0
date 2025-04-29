from celery import Celery
import redis
import celeryconfig

celery = Celery(
    "task",
    broker=celeryconfig.broker_url,
    backend=celeryconfig.result_backend,
    include=[
        "app.tasks",
        "app.async_db_tasks"
    ]
)
celery.conf.update({
    "broker_url": celeryconfig.broker_url,
    "result_backend": celeryconfig.result_backend,
})

redis_conn = redis.Redis(host="redis", port=6379, db=0)