# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from SubSync.views import cancel_scheduled_tasks
# from .models import Reminder, Subscription
# from .utils import schedule_reminder_tasks

# import logging
# logger = logging.getLogger(__name__)

# @receiver(post_save, sender=Reminder)
# def handle_reminder_creation(sender, instance, created, **kwargs):
#     """Schedule tasks when a new reminder is created."""
#     if created:
#         try:
#             logger.info(f"New reminder created with ID: {instance.id}")
#             subscription = instance.subscription_reminder.first()
#             if subscription:
#                 logger.info(f"Scheduling tasks for subscription ID: {subscription.id}")
#                 schedule_reminder_tasks(subscription, instance)
#         except Exception as e:
#             logger.error(f"Error handling reminder creation: {e}")

# @receiver(post_save, sender=Reminder)
# def handle_reminder_creation(sender, instance, created, **kwargs):
#     """Schedule tasks when a new reminder is created."""
#     print("\n**********************************************signals.py***************************************************************************************")

#     logger.info("handle_reminder_creation signal received")
#     if created:
#         try:
#             logger.info(f"New reminder created with ID: {instance.id}")

#             # Check if the reminder is related to a subscription
#             if instance.subscription_reminder.exists():
#                 reminder_subscription = instance.subscription_reminder.first()
#                 logger.info(f"subscription_reminder object: {type(reminder_subscription)}")
#                 # if subscription:
#                 #     logger.info(f"Scheduling tasks for subscription ID: {subscription.id}")
#                 #     schedule_reminder_tasks(subscription, instance)
#                 if hasattr(reminder_subscription, "subscription"):
#                     subscription = reminder_subscription.subscription  # Correctly get Subscription
#                     user_id = subscription.user.id if hasattr(subscription, "user") else None  # Extract user ID
#                     logger.info(f"Scheduling tasks for subscription ID: {subscription.id}, User ID: {user_id}")
#                     schedule_reminder_tasks(subscription, instance)  # Pass correct object
#                 else:
#                     logger.error(f"ReminderSubscription {reminder_subscription.id} does not have a linked Subscription")

#             # Check if the reminder is related to hardware
#             elif hasattr(instance, 'hardware_reminder') and instance.hardware_reminder.exists():
#                 hardware = instance.hardware_reminder.first()
#                 user_id = hardware.user.id if hasattr(hardware, "user") else None 
#                 if hardware:
#                     logger.info(f"Scheduling tasks for hardware ID: {hardware.id},User id:{user_id}")
#                     schedule_reminder_tasks(hardware, instance)

#         except Exception as e:
#             logger.error(f"Error handling reminder creation: {e}")


# @receiver(post_save, sender=Subscription)
# def handle_subscription_update(sender, instance , created, **kwargs):
#     """Cancel scheduled tasks when subscription is updated to 'Paid'."""
#     if not created:  # Only proceed if this is an update, not a creation
#         if instance.payment_status == "Paid":
#             logger.info(f"Subscription ID {instance.id} is paid. Cancelling scheduled tasks.")
#             # reminder = instance.reminder_set.first()  # Get the associated reminder
#             reminder = instance.reminder_subscriptions.first()
#             if reminder:
#                 cancel_scheduled_tasks(reminder)