# from celery import shared_task
# from django.core.mail import send_mail
# from SubSync.models import Reminder
# from SubscriptionManagementSystem.settings import DEFAULT_FROM_EMAIL
# import logging

# logger = logging.getLogger(__name__)

# @shared_task
# def send_reminder_email(reminder_id):
#     """Send reminder email and update the next reminder date."""
#     logger.info(f"Starting send_reminder_email task for reminder ID: {reminder_id}")
#     try:
#         reminder = Reminder.objects.get(id=reminder_id)

#         # Fetch the associated ReminderSubscription
#         reminder_for_subscription = reminder.subscription_reminder.first()
#         logger.info(f"Reminder for subscription: {reminder_for_subscription}")
#         if not reminder_for_subscription:
#             logger.error(f"No subscription found for reminder ID: {reminder_id}")
#             return
        
#         # Fetch the Subscription from the ReminderSubscription
#         subscription = reminder_for_subscription.subscription
#         logger.info(f"Subscription found: {subscription}")
        
#         logger.info(f"Sending reminder email for reminder ID: {reminder_id}")

#         subject = f"Reminder: For {reminder.reminder_type}"
#         message = reminder.custom_message or "This is a reminder for your subscription."
#         recipients = reminder.recipients.split(",") if reminder.recipients else []
#         logger.info(f"Recipients: {recipients}")

#         send_mail(subject, message, DEFAULT_FROM_EMAIL, recipients)
#         logger.info("Email sent successfully.")

#         if subscription:
#             reminder_dates = reminder.calculate_all_reminder_dates(subscription)
#             logger.info(f"Calculated reminder dates: {reminder_dates}")
#             print(reminder_dates)

#             if reminder_dates:
#                 next_reminder_date = reminder_dates[0]  # Get the next reminder date
#                 reminder.reminder_date = next_reminder_date
#                 reminder.save()
#                 logger.info(f"Updated reminder_date to: {next_reminder_date}")
                
#     except Exception as e:
#         logger.error(f"Error sending reminder email: {e}")





from datetime import timedelta
import os
from django.utils import timezone
from celery import shared_task
from django.core.mail import send_mail
from SubSync.models import Reminder
from SubscriptionManagementSystem.settings import DEFAULT_FROM_EMAIL

import logging

logger = logging.getLogger(__name__)

# @shared_task
# def send_reminder_notification(reminder_id):
#     print("\n*************************************************************************************************************************************")

#     """Send reminder notifications based on the selected notification method."""
#     logger.info(f"Starting send_reminder_notification task for reminder ID: {reminder_id}")

#     try:
#         reminder = Reminder.objects.get(id=reminder_id)
#         subscription = reminder.subscription_reminder.first().subscription if reminder.subscription_reminder.exists() else None
#         logger.info(f"Subscription found: {subscription}")

#         if not subscription:
#             logger.error(f"No subscription found for reminder ID: {reminder_id}")
#             return
        
#         # Stop reminders if the subscription is paid
#         # if subscription.payment_status == "Paid":
#         #     logger.info(f"Subscription ID {subscription.id} is paid. Stopping reminders.")
#         #     return
        
#         logger.info(f"Sending reminder for reminder ID: {reminder_id}")

#         if subscription.status == "Expired" or subscription.payment_status == "Unpaid":
#             # Update reminder_type to "overdue" if it's not already set
#             if reminder.reminder_type != "overdue":
#                 reminder.reminder_type = "overdue"
#                 reminder.save()
#                 logger.info(f"Updated reminder_type to 'overdue' for reminder ID: {reminder_id}")
#             logger.info(f"Sending overdue reminder for reminder ID: {reminder_id}")

#             subject = f"Overdue Reminder: {reminder.reminder_type} for "
#             message = "This is an overdue reminder for your subscription ."

#         else:
#             subject = f"Reminder: {reminder.reminder_type} for active subscription "
#             message = reminder.custom_message or "This is a reminder for your subscription ."
#         recipients = reminder.recipients.split(",") if reminder.recipients else []
#         logger.info(f"Recipients: {recipients}")

#         # Send notifications based on the selected method
#         if reminder.notification_method == "email" or reminder.notification_method == "both":
#             if recipients:
#                 try:
#                     logger.info(f"Sending email reminder to: {recipients}")
#                     send_mail(subject, message, DEFAULT_FROM_EMAIL, recipients)
#                     logger.info("Email notification sent successfully.")
#                 except Exception as e:
#                     logger.error(f"Failed to send email notification: {e}")
#             else:
#                 logger.warning("No recipients found for email notification.")

#         if reminder.notification_method == "sms" or reminder.notification_method == "both":
#             phone_numbers = reminder.phone_numbers.split(",") if reminder.phone_numbers else []
#             if phone_numbers:
#                 try:
#                     logger.info(f"Sending SMS reminder to: {phone_numbers}")
#                     send_sms_notification(phone_numbers, message)
#                     logger.info("SMS notification sent successfully.")
#                 except Exception as e:
#                     logger.error(f"Failed to send SMS notification: {e}")
#             else:
#                 logger.warning("No phone numbers found for SMS notification.")

#         try:
#             logger.info("Sending in-app notification for reminder.")
#             send_in_app_notification(subscription, message)
#             # logger.info("In-app notification sent.")
#         except Exception as e:
#             logger.error(f"Failed to send in-app notification: {e}")
        
#         logger.info("Reminder notifications sent successfully.")
        
#         # Debugging: Log subscription status and payment status again
#         logger.info(f"Subscription status: {subscription.status}")
#         logger.info(f"Subscription payment status: {subscription.payment_status}")

#         if subscription.status == "Expired" or subscription.payment_status == "Unpaid":
#             # Schedule the next overdue reminder
#             today=timezone.now().date()
#             logger.info(f"Today's date: {today}, Current reminder date: {reminder.reminder_date}")
#             # if not reminder.reminder_date or reminder.reminder_date < next_overdue_reminder_date:
#             if  reminder.reminder_date < today:
#                 next_overdue_reminder_date = today + timedelta(days=3)  # Adjust the interval as needed
#                 reminder.reminder_date = next_overdue_reminder_date
#                 reminder.save()
#                 logger.info(f"Scheduled next overdue reminder for: {next_overdue_reminder_date}")
#             else:
#                 logger.info("Next overdue reminder already scheduled.")
#         else:
#             # Update next reminder date
#             reminder_dates = reminder.calculate_all_reminder_dates(subscription)
#             logger.info(f"Calculated reminder dates: {reminder_dates}")
#             if reminder_dates:
#                 # Find the index of the current reminder date
#                 current_date = timezone.now().date()
#                 try:
#                     current_index = reminder_dates.index(current_date)
#                 except ValueError:
#                     logger.warning(f"Current date {current_date} not found in reminder dates. Skipping reminder date update.")
#                     return

#                 # Check if there is a next date in the list
#                 if current_index + 1 < len(reminder_dates):
#                     next_reminder_date = reminder_dates[current_index + 1]
#                     reminder.reminder_date = next_reminder_date
#                     reminder.save()
#                     logger.info(f"Updated reminder_date to: {next_reminder_date}")
#                 else:
#                     logger.info("No more reminder dates. Resetting reminder_date to None.")
#                     reminder.reminder_date = None
#                     reminder.save()
#                     # next_reminder_date = reminder_dates[0]
#                     # reminder.reminder_date = next_reminder_date
#                     # reminder.save()
#                     logger.info(f"Updated reminder_date to: {next_reminder_date}")
#             else:
#                 logger.warning("No reminder dates calculated. Skipping reminder date update.")

#     except Exception as e:
#         logger.error(f"Error sending reminder notifications: {e}")

@shared_task
def send_reminder_notification(reminder_id):
    """Send reminder notifications based on the selected notification method."""
    print("\n*************************************************************************************************************************************")

    logger.info(f"Starting send_reminder_notification task for reminder ID: {reminder_id}")

    try:
        reminder = Reminder.objects.get(id=reminder_id)
        
        # Determine whether the reminder is for a Subscription or Hardware
        subscription = reminder.subscription_reminder.first().subscription if reminder.subscription_reminder.exists() else None
        hardware = reminder.hardware_reminder.first().hardware if hasattr(reminder, 'hardware_reminder') and reminder.hardware_reminder.exists() else None

        # Identify entity type
        entity = subscription if subscription else hardware
        entity_type = "Subscription" if subscription else "Hardware"
        # print(f"entity:{entity_type}")
        
        if not entity:
            logger.error(f"No subscription or hardware found for reminder ID: {reminder_id}")
            return

        logger.info(f"{entity_type} found: {entity.id}")

        # Fetch subscription name from related tables
        subscription_name = None

        if hasattr(entity, 'software_detail'):
            subscription_name = entity.software_detail.software_name
        elif hasattr(entity, 'billing'):
            subscription_name = entity.billing.utility_name
        elif hasattr(entity, 'domain'):
            subscription_name = entity.domain.domain_name
        else:
            subscription_name = "Unknown Subscription"

        logger.info(f"Subscription Name: {subscription_name}")


        # Stop reminders if necessary (for subscriptions)
        # if entity_type == "Subscription" and entity.payment_status == "Paid":
        #     logger.info(f"Subscription ID {entity.id} is paid. Stopping reminders.")
        #     return

        logger.info(f"Sending reminder for reminder ID: {reminder_id}")

        # Handle overdue reminders
        if entity_type == "Subscription" and (entity.status == "Expired" or entity.payment_status == "Unpaid"):
            if reminder.reminder_type != "overdue":
                reminder.reminder_type = "overdue"
                reminder.save()
                logger.info(f"Updated reminder_type to 'overdue' for reminder ID: {reminder_id}")

            subject = f"Overdue Reminder for {entity_type}"
            message = f"This is an overdue reminder for your {entity.subscription_category} {entity_type.lower()}  - {subscription_name}."
        
        else:
            subject = f"Reminder: {reminder.reminder_type} for {entity_type}"
            message = reminder.custom_message or f"This is a reminder for your {entity_type.lower()}."

        recipients = reminder.recipients.split(",") if reminder.recipients else []
        logger.info(f"Recipients: {recipients}")

        # Send notifications based on the selected method
        if reminder.notification_method in ["email", "both"]:
            if recipients:
                try:
                    logger.info(f"Sending email reminder to: {recipients}")
                    send_mail(subject, message, DEFAULT_FROM_EMAIL, recipients)
                    logger.info("Email notification sent successfully.")
                except Exception as e:
                    logger.error(f"Failed to send email notification: {e}")
            else:
                logger.warning("No recipients found for email notification.")

        if reminder.notification_method in ["sms", "both"]:
            phone_numbers = reminder.phone_numbers.split(",") if reminder.phone_numbers else []
            if phone_numbers:
                try:
                    logger.info(f"Sending SMS reminder to: {phone_numbers}")
                    send_sms_notification(phone_numbers, message)
                    logger.info("SMS notification sent successfully.")
                except Exception as e:
                    logger.error(f"Failed to send SMS notification: {e}")
            else:
                logger.warning("No phone numbers found for SMS notification.")

        try:
            logger.info(f"Sending in-app notification for {entity_type}.")
            send_in_app_notification(entity, message)
            logger.info("In-app notification sent.")
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")

        logger.info(f"Reminder notifications sent successfully for {entity_type} ID: {entity.id}")

        # Update next reminder date logic
        today = timezone.now().date()
        logger.info(f"Today's date: {today}, Current reminder date: {reminder.reminder_date}")

        if entity_type == "Subscription" and (entity.status == "Expired" or entity.payment_status == "Unpaid"):
            if reminder.reminder_date < today:
                next_overdue_reminder_date = today + timedelta(days=3)  # Adjust interval as needed
                reminder.reminder_date = next_overdue_reminder_date
                reminder.save()
                logger.info(f"Scheduled next overdue reminder for: {next_overdue_reminder_date}")
            else:
                logger.info("Next overdue reminder already scheduled.")

        else:
            reminder_dates = reminder.calculate_all_reminder_dates(entity)
            logger.info(f"Calculated reminder dates: {reminder_dates}")

            if reminder_dates:
                current_date = timezone.now().date()
                try:
                    current_index = reminder_dates.index(current_date)
                except ValueError:
                    logger.warning(f"Current date {current_date} not found in reminder dates. Skipping reminder date update.")
                    return

                if current_index + 1 < len(reminder_dates):
                    next_reminder_date = reminder_dates[current_index + 1]
                    reminder.reminder_date = next_reminder_date
                    reminder.save()
                    logger.info(f"Updated reminder_date to: {next_reminder_date}")
                else:
                    logger.info("No more reminder dates. Resetting reminder_date to None.")
                    reminder.reminder_date = None
                    reminder.save()

    except Exception as e:
        logger.error(f"Error sending reminder notifications: {e}")



import logging
from twilio.rest import Client
from django.conf import settings

logger = logging.getLogger(__name__)

# Load Twilio credentials from Django settings (or you can use environment variables)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')  # Your Twilio sender number

def send_sms_notification(phone_numbers, message):
    """Send SMS notifications using Twilio."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        for phone in phone_numbers:
            if phone.strip():
                logger.info(f"Sending SMS to {phone}: {message}")
                message_response = client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone.strip()
                )
                logger.info(f"SMS sent successfully to {phone}. SID: {message_response.sid}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False


# def send_in_app_notification(subscription, message):
#     from SubSync.tasks import send_reminder_notification
#     """Mock function to send in-app notifications."""
#     try:
#         # Assuming you have a Notification model
#         from SubSync.models import Notification

#         Notification.objects.create(
#             subscription=subscription,
#             message=message
#         )
#         logger.info(f"In-app notification created for subscription ID: {subscription.id}")
#         return True
#     except Exception as e:
#         logger.error(f"Failed to create in-app notification: {e}")
#         return False

def send_in_app_notification(entity, message):
    """Send in-app notifications for subscriptions and hardware."""
    try:
        # Import Notification model
        from SubSync.models import Notification

        # Determine entity type
        entity_type = "Subscription" if hasattr(entity, "payment_status") else "Hardware"
        entity_id = entity.id

        # Create in-app notification
        Notification.objects.create(
            subscription=entity if entity_type == "Subscription" else None,
            hardware=entity if entity_type == "Hardware" else None,
            message=message
        )

        logger.info(f"In-app notification created for {entity_type} ID: {entity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to create in-app notification: {e}")
        return False
