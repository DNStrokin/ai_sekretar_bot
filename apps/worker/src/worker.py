"""
Celery Worker Configuration

Фоновые задачи: STT, обработка ссылок, файлов.
"""

from celery import Celery

from .config import settings

# Create Celery app
celery_app = Celery(
    "sekretar_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Dead letter queue for failed tasks
celery_app.conf.task_routes = {
    "src.tasks.*": {"queue": "default"},
}
