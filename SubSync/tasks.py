# # # from celery import shared_task
# # # from django.utils.timezone import now
# # # from .models import Reminder

# # # @shared_task
# # # def process_pending_reminders():
# # #     """Check and send reminders that are due"""
# # #     reminders = Reminder.objects.filter(reminder_status='pending', reminder_date=now().date())
    
# # #     for reminder in reminders:
# # #         reminder.schedule_reminder()
# # #         reminder.reminder_status = 'sent'
# # #         reminder.save()


# # # subscriptions/tasks.py
# # from celery import shared_task
# # from django.utils import timezone
# # from datetime import timedelta
# # from .models import Reminder
# # from django.core.mail import send_mail

# # @shared_task
# # def send_subscription_reminder():
# #     """Send subscription reminders to users based on reminder_date."""
# #     today = timezone.now().date()
    
# #     reminders = Reminder.objects.filter(
# #         reminder_date=today, 
# #         reminder_status="pending"
# #     )

# #     for reminder in reminders:
# #         subject = f"Reminder: {reminder.reminder_type.capitalize()}"
# #         message = reminder.custom_message or f"Your {reminder.reminder_type} is due soon."
# #         recipient_list = reminder.recipients.split(",") if reminder.recipients else []

# #         if recipient_list:
# #             send_mail(subject, message, "noreply@example.com", recipient_list)

# #         reminder.reminder_status = "sent"
# #         reminder.save()

# #     return f"Sent {reminders.count()} reminders."


# from celery import shared_task
# from django.core.mail import send_mail

# from SubSync.models import Reminder

# @shared_task
# def send_reminder_email(reminder_id):
#     """Send reminder email for a given reminder."""
#     reminder = Reminder.objects.get(id=reminder_id)
#     subject = f"Reminder: {reminder.reminder_type}"
#     message = reminder.custom_message or "This is a reminder for your subscription."
#     recipients = reminder.recipients.split(",") if reminder.recipients else []
#     send_mail(subject, message, "noreply@example.com", recipients)

from celery import shared_task
from django.core.mail import send_mail
from SubSync.models import Reminder
# from SubSync.views import calculate_all_reminder_dates
from SubscriptionManagementSystem.settings import DEFAULT_FROM_EMAIL
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_reminder_email(reminder_id):
    """Send reminder email and update the next reminder date."""
    logger.info(f"Starting send_reminder_email task for reminder ID: {reminder_id}")
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        
        subscription = reminder.subscription_reminder.first()
        if not subscription:
            logger.error(f"No subscription found for reminder ID: {reminder_id}")
            return
        
        logger.info(f"Sending reminder email for reminder ID: {reminder_id}")

        subject = f"Reminder: {reminder.reminder_type}"
        message = reminder.custom_message or "This is a reminder for your subscription."
        recipients = reminder.recipients.split(",") if reminder.recipients else []
        logger.info(f"Recipients: {recipients}")

        send_mail(subject, message, DEFAULT_FROM_EMAIL, recipients)
        logger.info("Email sent successfully.")

        # Update the reminder_date to the next reminder date
        subscription = reminder.subscription_reminder.first()
        if subscription:
            # reminder_dates = calculate_all_reminder_dates(subscription, reminder)
            reminder_dates = reminder.calculate_all_reminder_dates(subscription)
            if reminder_dates:
                next_reminder_date = reminder_dates[0]  # Get the next reminder date
                reminder.reminder_date = next_reminder_date
                reminder.save()
                logger.info(f"Updated reminder_date to: {next_reminder_date}")
                
    except Exception as e:
        logger.error(f"Error sending reminder email: {e}")