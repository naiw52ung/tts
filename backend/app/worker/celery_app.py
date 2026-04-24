from celery import Celery

from app.core.config import settings

broker_url = settings.redis_url
backend_url = settings.redis_url
if settings.celery_task_always_eager or settings.redis_url.startswith("memory://"):
    broker_url = "memory://"
    backend_url = "cache+memory://"

celery_app = Celery("legendai_worker", broker=broker_url, backend=backend_url)
celery_app.conf.update(
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
)
