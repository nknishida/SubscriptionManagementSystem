from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reminder, Subscription
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



from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Subscription)
def handle_subscription_update(sender, instance , created, **kwargs):
    """Cancel scheduled tasks when subscription is updated to 'Paid'."""
    if not created:  # Only proceed if this is an update, not a creation
        if instance.payment_status == "Paid":
            logger.info(f"Subscription ID {instance.id} is paid. Cancelling scheduled tasks.")
            reminder = instance.reminder_set.first()  # Get the associated reminder
            if reminder:
                cancel_scheduled_tasks(reminder)