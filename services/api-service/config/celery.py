import os

from celery import Celery

env = os.environ.get("DJANGO_ENV", "local")


# Tell Celery where Django settings are
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env}")


app = Celery("config")


# Load settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")


# Auto discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
