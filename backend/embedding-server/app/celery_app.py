from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "embedding_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.batch_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
