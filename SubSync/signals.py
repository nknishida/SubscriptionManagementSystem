# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Subscription, Reminder, ReminderSubscription
# from datetime import timedelta

# @receiver(post_save, sender=Subscription)
# def create_subscription_reminder(sender, instance, created, **kwargs):
#     """Automatically create a reminder when a subscription is created."""
#     if created:
#         print(f"Creating reminder for subscription: {instance.name}")  # Debugging
#         reminder_date = instance.renewal_date - timedelta(days=7)
#         reminder = Reminder.objects.create(
#             reminder_type='renewal',
#             reminder_days_before=7,
#             reminder_date=reminder_date,
#             notification_method='email',
#             sent_to=instance.reminder_email,
#             custom_message=f"Reminder: Your subscription for {instance.name} is due for renewal.",
#         )
#         ReminderSubscription.objects.create(reminder=reminder, subscription=instance)

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