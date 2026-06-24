import os

from celery import Celery
from celery.signals import task_postrun, worker_process_init
from django.db import close_old_connections

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_process_init.connect
def _close_stale_db_connections_on_worker_start(**_kwargs):
    close_old_connections()


@task_postrun.connect
def _close_db_connections_after_task(**_kwargs):
    close_old_connections()
