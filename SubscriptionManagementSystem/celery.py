# celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SubscriptionManagementSystem.settings')

app = Celery('SubscriptionManagementSystem')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.enable_utc = False
app.conf.timezone = 'Asia/Kolkata'
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'subscriptions.tasks.send_due_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
    'update-statuses': {
        'task': 'SubSync.tasks.update_subscriptions_status',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
    'send-daily-hardware-reminders': {
        'task': 'SubSync.tasks.send_hardware_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
    'send-daily-customer-reminders': {
        'task': 'SubSync.tasks.send_customer_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
}