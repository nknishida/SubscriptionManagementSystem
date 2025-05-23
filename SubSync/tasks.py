from datetime import timedelta
import os
from django.utils import timezone
from celery import shared_task
from django.core.mail import send_mail
from SubSync.models import Reminder,HardwareService,Notification, Subscription, Hardware, Customer, User, Warranty,ReminderCustomer,ReminderHardware
from SubscriptionManagementSystem.settings import DEFAULT_FROM_EMAIL
from django.utils.timezone import now
from django.db import transaction,connection
from django.template.loader import render_to_string
from twilio.rest import Client
from django.conf import settings
from django.utils import timezone
import pytz
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import logging
logger = logging.getLogger(__name__)

# Load Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')  #Twilio sender number


@shared_task
def send_reminder_notification(reminder_id,user_id=None):
    """Send reminder notifications based on the selected notification method."""
    print("\n**********************************************tasks.py***************************************************************************************")

    logger.info(f"Starting send_reminder_notification task for reminder ID: {reminder_id}")

    try:
        reminder = Reminder.objects.get(id=reminder_id)
        user = User.objects.get(id=user_id) if user_id else None  # Fetch user details
        # Extract user phone numbers if available
        user_phone_number = user.phone_numbers.split(",") if user and user.phone_numbers else []
        
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

        if reminder.notification_method in ["sms", "both"] and user_phone_number :
            # user_phone_number = request.user.phone_number
            # phone_numbers = reminder.phone_numbers.split(",") if reminder.phone_numbers else []
            # if user_phone_number:
                # phone_numbers = [user_phone_number]
            try:
                logger.info(f"Sending SMS reminder to: {user_phone_number}")
                send_sms_notification(user_phone_number, message)
                logger.info("SMS notification sent to {user_phone_number} successfully.")
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


@shared_task
def delete_old_recycle_bin_items():
    """
    Automatically delete items that have been in the recycle bin for more than 30 days.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Delete old items
    Subscription.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()
    Hardware.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()
    Customer.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()

    return "Old items permanently deleted"

@shared_task
def update_subscriptions_status():
    today = now().date()

    # Debug: Check database connection
    if connection.closed_in_transaction:
        logger.warning("Database connection was closed. Reconnecting...")
        connection.close()

    logger.info("Starting subscription status update task")
    
    subscriptions = Subscription.objects.filter(is_deleted=False)
    logger.info(f"Found {subscriptions.count()} active subscriptions to check.")

    to_update = []

    for subscription in subscriptions:
        original_status = subscription.status
        original_payment_status = subscription.payment_status
        original_last_payment = subscription.last_payment_date
        original_next_payment = subscription.next_payment_date

        logger.info(
            f"Checking subscription {subscription.id} ,"
            # end_date={subscription.end_date}, "
            f"next_payment_date={subscription.next_payment_date}, today={today}"
        )

        # Check if the end date has passed
        # if subscription.end_date and today > subscription.end_date:
        #     logger.info(f"Updating subscription {subscription.id} to Inactive")
        #     subscription.status = "Inactive"
        #     subscription.payment_status = "Unpaid"
        
        if subscription.next_payment_date:
            if today > subscription.next_payment_date:
                if subscription.auto_renewal:
                    subscription.status = "Active"
                    subscription.payment_status = "Paid"
                    # Set last payment date to today or next_payment_date
                    subscription.last_payment_date = subscription.next_payment_date or today

                    # Recalculate the next payment date
                    subscription.calculate_next_payment_date()
                    logger.info(
                        f"Subscription {subscription.id}: Auto-renewed - "
                        f"last_payment_date set to {subscription.last_payment_date}, "
                        f"next_payment_date set to {subscription.next_payment_date}"
                    )
                else:
                    subscription.status = "Expired"
                    logger.info(f"Subscription {subscription.id}: Auto-renewal is disabled, marking as Expired")
                    subscription.payment_status = "Pending"
            else:
                subscription.payment_status = "Paid"
                subscription.status = "Active" 

        # Add only if status or payment_status changed
        if (subscription.status != original_status or subscription.payment_status != original_payment_status or subscription.last_payment_date != original_last_payment or subscription.next_payment_date != original_next_payment):
            logger.info(
                f"Subscription {subscription.id} updated: "
                f"status={original_status} -> {subscription.status}, "
                f"payment_status={original_payment_status} -> {subscription.payment_status}"
            )
            to_update.append(subscription)
    
    # Perform a bulk update if any records changed
    if to_update:
        logger.info(f"Updating {len(to_update)} subscriptions in bulk...")
        with transaction.atomic():
            Subscription.objects.bulk_update(to_update, ["status", "payment_status", "last_payment_date", "next_payment_date"])
        logger.info("Bulk update successful.")
    else:
        logger.info("No subscriptions needed updating.")

    logger.info("Subscription status update task completed.")

@shared_task
def update_warranty_status():
    """Task to update warranty status for all hardware."""
    today = now().date()
    
    warranties = Warranty.objects.all()
    
    for warranty in warranties:
        
        warranty.save()
    
    return "Warranty status updated successfully"


@shared_task
def update_customer_status():
    """Automatically updates customer status based on end_date."""
    today = now().date()
    customers = Customer.objects.filter(is_deleted=False)

    logger.info(f"Starting customer status update task. Found {customers.count()} customers to check.")

    to_update = []

    for customer in customers:
        original_status = customer.status

        logger.info(f"Checking customer {customer.id}: end_date={customer.end_date}, today={today}")

        #  If end_date is over, mark as Inactive
        if customer.end_date and today > customer.end_date:
            logger.info(f"Customer {customer.id}: End date passed, marking as Inactive")
            customer.status = "Inactive"

        # Add to bulk update if status changed
        if customer.status != original_status:
            logger.info(f"Customer {customer.id} updated: status={original_status} -> {customer.status}")
            to_update.append(customer)

    #  Perform bulk update for efficiency
    if to_update:
        with transaction.atomic():
            Customer.objects.bulk_update(to_update, ["status"])
        logger.info(f"Updated {len(to_update)} customers in bulk.")

    logger.info("Customer status update task completed.")

@shared_task
def clean_old_history(days_to_keep=90):
    """Clean history records older than X days"""
    from django.db.models import Q
    from django.utils import timezone
    from SubSync.models import Subscription
    
    cutoff = timezone.now() - timezone.timedelta(days=days_to_keep)
    
    # Delete in chunks
    Subscription.history.filter(history_date__lt=cutoff).delete()


@shared_task
def update_hardware_service_statuses():
    """
    Periodic task to update status of all hardware services based on their dates
    """
    today = timezone.now().date()
    soon_threshold = today + timedelta(days=7)
    
    try:
        # Get all services that might need status updates
        services = HardwareService.objects.all()
        
        updated_counts = {
            'to_active': 0,
            'to_maintenance_soon': 0,
            'to_maintenance_due': 0,
            'unchanged': 0
        }
        
        for service in services:
            original_status = service.status
            
            # Determine new status
            if service.next_service_date:
                if service.next_service_date <= today:
                    new_status = 'Maintenance Due'
                elif service.next_service_date <= soon_threshold:
                    new_status = 'Maintenance Soon'
                else:
                    new_status = 'Active'
            else:
                new_status = 'Active'
            
            # Only update if status changed
            if new_status != original_status:
                service.status = new_status
                service.save()
                updated_counts[f'to_{new_status.lower().replace(" ", "_")}'] += 1
            else:
                updated_counts['unchanged'] += 1
        
        logger.info(
            f"Hardware service status update completed. "
            f"Updated to Active: {updated_counts['to_active']}, "
            f"Updated to Maintenance Soon: {updated_counts['to_maintenance_soon']}, "
            f"Updated to Maintenance Due: {updated_counts['to_maintenance_due']}, "
            f"Unchanged: {updated_counts['unchanged']}"
        )
        return updated_counts
        
    except Exception as e:
        logger.error(f"Error updating hardware service statuses: {str(e)}")
        raise


@shared_task
def send_due_reminders():
    """Send all reminders that are due today."""
    
    # Get current time in configured timezone
    tz = pytz.timezone('Asia/Kolkata')
    now = timezone.now().astimezone(tz)
    
    today = now.date()
    logger.info(f"=== Starting reminder processing for {today} ===")

    upcoming_subscriptions = Subscription.objects.filter(
        next_payment_date__lte=today + timedelta(days=7),  # Within next 10 days
        payment_status="Paid",is_deleted=False
    )
    
    for subscription in upcoming_subscriptions:
        if (subscription.next_payment_date - today).days <= 7:
            subscription.payment_status = "Pending"
            subscription.save()
            logger.info(f"Updated subscription {subscription.id} to Pending (due {subscription.next_payment_date})")
        
    due_reminders = Reminder.objects.filter(
        reminder_date=today,
        reminder_status="pending"
    ).prefetch_related('subscription_reminder__subscription')

    logger.info(f"Found {due_reminders.count()} reminders to process")
    
    for reminder in due_reminders:
        logger.info(f"Processing reminder ID: {reminder.id}")
        subscription = reminder.subscription_reminder.first().subscription
        logger.info(f" - Subscription: {subscription.id} ({subscription.status})")

        if today >= subscription.next_payment_date:
                subscription.payment_status = "Pending"
                subscription.save()        
        
        # Check if we should still send this reminder
        if subscription.is_deleted or not reminder.should_send_reminder(subscription):
            logger.info(" - Skipping: shouldn't send per business rules")
            reminder.reminder_status = "cancelled"
            reminder.save()
            continue
            
        # Prepare and send the reminder
        try:
            logger.info(" - Sending reminder...")
            # context = {
            #     'subscription': subscription,
            #     'reminder': reminder,
            #     'is_overdue': subscription.payment_status == "Unpaid"
            # }
            is_overdue = subscription.next_payment_date < today if subscription.next_payment_date else False
            if is_overdue:
                    subject = f"URGENT: Overdue Payment for {subscription.provider.provider_name}"
                    message = f"""
                    OVERDUE SUBSCRIPTION PAYMENT
                    ----------------------------
                    
                    Provider: {subscription.provider.provider_name}
                    Category: {subscription.subscription_category}
                    Amount Due: ${subscription.cost}
                    Due Date: {subscription.next_payment_date}
                    Days Overdue: {(today - subscription.next_payment_date).days}
                    
                    {reminder.custom_message or 'Please make payment immediately to avoid service disruption.'}
                    """
            else:
                    subject = f"Upcoming Payment for {subscription.provider.provider_name}"
                    message = f"""
                    SUBSCRIPTION RENEWAL REMINDER
                    ----------------------------
                    
                    Provider: {subscription.provider.provider_name}
                    Category: {subscription.subscription_category}
                    Amount Due: ${subscription.cost}
                    Due Date: {subscription.next_payment_date}
                    Days Remaining: {(subscription.next_payment_date - today).days}
                    
                    {reminder.custom_message or 'Please renew your subscription to avoid service interruption.'}
                    """
            
            # Email reminder
            if reminder.notification_method in ['email', 'both']:
                subject = "Subscription Reminder"
                # if context['is_overdue']:
                #     subject = "URGENT: Overdue Subscription Payment"
                    
                # message = render_to_string('reminder_email.html', context)
                
                # message = f"""
                # Subscription Reminder
                # ---------------------
                
                # Provider: {subscription.provider.provider_name}
                # Category: {subscription.subscription_category}
                # Amount: ${subscription.cost}
                # Due Date: {subscription.next_payment_date}
                
                # {reminder.custom_message or 'Please renew your subscription to avoid service interruption.'}
                # """
                send_mail(
                    subject,
                    message.strip(),
                    DEFAULT_FROM_EMAIL,
                    [r.strip() for r in reminder.recipients.split(',')],
                    html_message=message
                )
            
            # SMS reminder (implement your SMS gateway integration)
            if reminder.notification_method in ['sms', 'both']:
                    sms_message = f"{subject}: Due {subscription.next_payment_date}. {message[:100]}..."
                    # send_sms_notification(reminder.recipients.split(','), sms_message)
                    send_sms_notification(os.getenv('TWILIO_DEFAULT_PHONE_NUMBER'), sms_message)

            user = subscription.user
                    
            notification =Notification.objects.create(
                user=user,
                subscription=subscription,
                title=f"Subscription Reminder: {subscription.provider.provider_name}",
                message=reminder.custom_message or f"Your {subscription.provider.provider_name} subscription is due on {subscription.next_payment_date}",
                notification_type='reminder',
                scheduled_for=timezone.now()
            )
            # Send WebSocket message
            try:
                channel_layer = get_channel_layer()
            except Exception as e:
                channel_layer = None
                logger.warning(f"Could not initialize channel layer: {str(e)}")
            if channel_layer is not None:
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'notifications_{user.id}',
                        {
                            'type': 'send_notification',
                            'content': {
                                'type': 'new_notification',
                                'notification': {
                                    'id': notification.id,
                                    'title': notification.title,
                                    'message': notification.message,
                                    'is_read': notification.is_read,
                                    'created_at': notification.created_at.isoformat()
                                }
                            }
                        }
                    )
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {str(e)}")
            else:
                logger.warning("No channel layer available - skipping WebSocket notification")

                
            # Mark as sent
            reminder.reminder_status = "sent"
            reminder.save()

            logger.info(" - Reminder sent successfully")
            future_dates = reminder.calculate_all_reminder_dates(subscription)
            future_dates = [d for d in future_dates if d > today]
            if future_dates:
                # Schedule the next earliest reminder
                next_reminder_date = min(future_dates)
                reminder.reminder_date = next_reminder_date
                reminder.reminder_status = "pending"
                reminder.save()
                logger.info(f"Next reminder scheduled for {next_reminder_date}")
            else:
                logger.info("No future reminders needed")
            logger.info(f"Reminder {reminder.id} processed successfully")
        
            # Schedule next reminder if needed
            # schedule_next_reminder(reminder, subscription)
            
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder.id}: {str(e)}")
            reminder.reminder_status = "failed"
            reminder.save()

def schedule_next_reminder(reminder, subscription):
    """Schedule the next reminder in the series."""
    future_dates = reminder.calculate_all_reminder_dates(subscription)
    future_dates = [d for d in future_dates if d > timezone.now().date()]
    
    if future_dates:
        next_date = min(future_dates)
        reminder.reminder_date = next_date
        reminder.reminder_status = "pending"
        reminder.save()


def send_sms_notification(phone, message):
    """Send SMS notifications using Twilio."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        phone_str = str(phone).strip()

        # for phone in phone_numbers:
        if phone_str:
            logger.info(f"Sending SMS to {phone_str}: {message}")
            message_response = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=phone_str.strip()
            )
            logger.info(f"SMS sent successfully to {phone_str}. SID: {message_response.sid}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False


@shared_task
def send_hardware_reminders():
    """Send all hardware reminders that are due today."""
        
    # Initialize timezone
    tz = pytz.timezone('Asia/Kolkata')
    now = timezone.now().astimezone(tz)
    today = now.date()
    logger.info(f"=== Starting hardware reminder processing for {today} ===")

    try:
        # Initialize channel layer for WebSocket notifications
        try:
            channel_layer = get_channel_layer()
        except Exception as e:
            channel_layer = None
            logger.warning(f"Channel layer not available: {str(e)}")

        # Process due reminders
        due_reminders = Reminder.objects.filter(
            reminder_date=today,
            reminder_status="pending",
            reminderhardware__isnull=False  # Only hardware-related reminders
        ).prefetch_related('reminderhardware_set__hardware__user')

        logger.info(f"Found {due_reminders.count()} hardware reminders to process")
        
        for reminder in due_reminders:
            try:
                # Get associated hardware
                hardware_reminder = reminder.reminderhardware_set.first()
                if not hardware_reminder:
                    continue
                    
                hardware = hardware_reminder.hardware
                user = hardware.user
                
                logger.info(f"Processing hardware reminder ID: {reminder.id} for {hardware}")

                # Determine reminder type and content
                if hardware_reminder.reminder_type == 'warranty':
                    subject = f"Warranty Expiry Reminder for {hardware}"
                    message = f"""
                    WARRANTY EXPIRY NOTICE
                    ----------------------
                    
                    Hardware: {hardware.hardware_type} ({hardware.serial_number})
                    Warranty Expiry Date: {hardware.warranty.warranty_expiry_date}
                    Days Remaining: {(hardware.warranty.warranty_expiry_date - today).days}
                    
                    {reminder.custom_message or 'Please renew your warranty to avoid additional costs.'}
                    """
                elif hardware_reminder.reminder_type == 'service':
                    subject = f"Service Due Reminder for {hardware}"
                    message = f"""
                    SERVICE DUE NOTICE
                    ------------------
                    
                    Hardware: {hardware.hardware_type} ({hardware.serial_number})
                    Next Service Date: {hardware.services.next_service_date}
                    Days Remaining: {(hardware.services.next_service_date - today).days}
                    
                    {reminder.custom_message or 'Please schedule your service appointment.'}
                    """
                else:
                    continue

                # Send notifications
                if reminder.notification_method in ['email', 'both']:
                    send_mail(
                        subject,
                        message.strip(),
                        settings.DEFAULT_FROM_EMAIL,
                        [r.strip() for r in reminder.recipients.split(',')],
                        # html_message=message
                    )
                
                if reminder.notification_method in ['sms', 'both']:
                    sms_message = f"{subject}: {message[:100]}..."
                    send_sms_notification(os.getenv('TWILIO_DEFAULT_PHONE_NUMBER'), sms_message)

                # Create in-app notification
                notification = Notification.objects.create(
                    user=user,
                    hardware=hardware,
                    title=subject,
                    message=message,
                    notification_type='hardware_reminder',
                    scheduled_for=timezone.now()
                )
                
                # Send WebSocket notification if available
                if channel_layer is not None:
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'notifications_{user.id}',
                            {
                                'type': 'send_notification',
                                'content': {
                                    'type': 'new_notification',
                                    'notification': {
                                        'id': notification.id,
                                        'title': notification.title,
                                        'message': notification.message,
                                        'is_read': notification.is_read,
                                        'created_at': notification.created_at.isoformat(),
                                        'hardware_id': hardware.id
                                    }
                                }
                            }
                        )
                    except Exception as e:
                        logger.error(f"WebSocket notification failed: {str(e)}")

                # Mark as sent
                reminder.reminder_status = "sent"
                reminder.save()

                logger.info(f"Hardware reminder {reminder.id} processed successfully")
                
            except Exception as e:
                logger.error(f"Failed to process hardware reminder {reminder.id}: {str(e)}")
                reminder.reminder_status = "failed"
                reminder.save()
                
    except Exception as e:
        logger.error(f"Critical error in send_hardware_reminders task: {str(e)}")


@shared_task
def send_customer_reminders():
    """Send all customer reminders that are due today."""
    
    # Initialize timezone
    tz = pytz.timezone('Asia/Kolkata')
    now = timezone.now().astimezone(tz)
    today = now.date()
    logger.info(f"=== Starting customer reminder processing for {today} ===")

    try:
        # Initialize channel layer for WebSocket notifications
        try:
            channel_layer = get_channel_layer()
        except Exception as e:
            channel_layer = None
            logger.warning(f"Channel layer not available: {str(e)}")

        # Process due reminders
        due_reminders = Reminder.objects.filter(
            reminder_date=today,
            reminder_status="pending",
            remindercustomer__isnull=False  # Only customer-related reminders
        ).prefetch_related('remindercustomer_set__customer__user')

        logger.info(f"Found {due_reminders.count()} customer reminders to process")
        
        for reminder in due_reminders:
            try:
                # Get associated customer
                customer_reminder = reminder.remindercustomer_set.first()
                if not customer_reminder:
                    continue
                    
                customer = customer_reminder.customer
                user = customer.user
                
                logger.info(f"Processing customer reminder ID: {reminder.id} for {customer.customer_name}")

                # Prepare notification content
                subject = f"Contract End Date Reminder for {customer.customer_name}"
                message = f"""
                CONTRACT END DATE NOTICE
                -----------------------
                
                Customer: {customer.customer_name}
                Contract End Date: {customer.end_date}
                Days Remaining: {(customer.end_date - today).days}
                
                {reminder.custom_message or 'Please review the contract renewal options.'}
                """

                # Send notifications
                if reminder.notification_method in ['email', 'both']:
                    send_mail(
                        subject,
                        message.strip(),
                        settings.DEFAULT_FROM_EMAIL,
                        [r.strip() for r in reminder.recipients.split(',')],
                        html_message=message
                    )
                
                if reminder.notification_method in ['sms', 'both']:
                    sms_message = f"{subject}: {message[:100]}..."
                    send_sms_notification(os.getenv('TWILIO_DEFAULT_PHONE_NUMBER'), sms_message)

                # Create in-app notification
                notification = Notification.objects.create(
                    user=user,
                    customer=customer,
                    title=subject,
                    message=message,
                    notification_type='customer_reminder',
                    scheduled_for=timezone.now()
                )
                
                # Send WebSocket notification if available
                if channel_layer is not None:
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'notifications_{user.id}',
                            {
                                'type': 'send_notification',
                                'content': {
                                    'type': 'new_notification',
                                    'notification': {
                                        'id': notification.id,
                                        'title': notification.title,
                                        'message': notification.message,
                                        'is_read': notification.is_read,
                                        'created_at': notification.created_at.isoformat(),
                                        'customer_id': customer.id
                                    }
                                }
                            }
                        )
                    except Exception as e:
                        logger.error(f"WebSocket notification failed: {str(e)}")

                # Mark as sent
                reminder.reminder_status = "sent"
                reminder.save()

                logger.info(f"Customer reminder {reminder.id} processed successfully")
                
            except Exception as e:
                logger.error(f"Failed to process customer reminder {reminder.id}: {str(e)}")
                reminder.reminder_status = "failed"
                reminder.save()
                
    except Exception as e:
        logger.error(f"Critical error in send_customer_reminders task: {str(e)}")