import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("event_ingestor")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from kombu import Queue

app.conf.task_queues = (
    Queue("processing_queue"),
    Queue("maintenance_queue"),
)

app.conf.task_default_queue = "processing_queue"

from celery.schedules import crontab

app.conf.beat_schedule = {
    "recover-stuck-every-minute": {
        "task": "apps.events.tasks.recover_stuck_processing",
        "schedule": 60.0,
    },
}
