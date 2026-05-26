import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notification.settings")

app = Celery("notification")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "requeue-missed-notifications": {
        "task": "notify_app.tasks.tasks.requeue_missed_notifications",
        "schedule": crontab(minute="*/1"),
    },
}

app.conf.timezone = "UTC"