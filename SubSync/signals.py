from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reminder
from .utils import schedule_reminder_tasks
import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Reminder)
def handle_reminder_creation(sender, instance, created, **kwargs):
    """Schedule tasks when a new reminder is created."""
    if created:
        try:
            logger.info(f"New reminder created with ID: {instance.id}")
            subscription = instance.subscription_reminder.first()
            if subscription:
                logger.info(f"Scheduling tasks for subscription ID: {subscription.id}")
                schedule_reminder_tasks(subscription, instance)
        except Exception as e:
            logger.error(f"Error handling reminder creation: {e}")