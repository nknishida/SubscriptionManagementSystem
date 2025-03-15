import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SubscriptionManagementSystem.settings')

# Create Celery app
app = Celery('SubscriptionManagementSystem')

# Load task modules from all registered Django app configs
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all Django apps
# app.autodiscover_tasks()
logger.info("Discovering tasks...")
app.autodiscover_tasks(['SubSync.tasks'])  # Ensure your tasks module is included
logger.info("Tasks discovered successfully.")

logger.info("Celery app configured successfully.")

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

