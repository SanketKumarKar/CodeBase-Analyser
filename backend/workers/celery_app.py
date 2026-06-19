"""
workers/celery_app.py — Celery application factory.

Import this in all Celery task modules.
Run with: celery -A workers.celery_app worker --loglevel=info
"""

from celery import Celery # asynchronous task queue framework
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "codebase_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.ingestion"],  # register task modules
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # fair dispatch for long-running tasks
    result_expires=86400,          # 24 hours
)
