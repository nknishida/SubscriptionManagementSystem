# celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SubscriptionManagementSystem.settings')

app = Celery('SubscriptionManagementSystem')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'Asia/Kolkata'
app.autodiscover_tasks()