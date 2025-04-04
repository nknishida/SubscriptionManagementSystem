# from datetime import datetime, time, timedelta, timezone
# from dateutil.relativedelta import relativedelta
# from celery import Celery
# from SubSync.tasks import send_reminder_email
# from .models import Reminder
# import logging
# logger = logging.getLogger(__name__)

# DEFAULT_RENEWAL_TIME = time(15, 30, 0)
# # DEFAULT_RENEWAL_TIME = "16:00:00"

# def schedule_reminder_tasks(subscription, reminder):
#     """Schedule tasks for all reminder dates."""
#     logger.info(f"Entering schedule_reminder_tasks for reminder ID: {reminder.id}")
    
#     try:
#         reminder_dates = reminder.calculate_all_reminder_dates(subscription)
#         logger.info(f"Scheduling tasks for reminder ID: {reminder.id}")
#         logger.info(f"Calculated reminder dates: {reminder_dates}")
        
#         for date in reminder_dates:
#             # logger.info(f"Scheduling task for date: {date} at time: {reminder.reminder_time}")
#             logger.info(f"Scheduling task for date: {date} at time: DEFAULT_RENEWAL_TIME")
#             # Schedule the task to run on the reminder date at the reminder time
#             # send_reminder_email.apply_async(args=[reminder.id], eta=timezone.datetime.combine(date, reminder.reminder_time))
            
#             logger.info(f"Task ETA: {datetime.combine(date, DEFAULT_RENEWAL_TIME)}")
#             send_reminder_email.apply_async(
#                 args=[reminder.id], 
#                 eta=datetime.combine(date, DEFAULT_RENEWAL_TIME)
#             )

#     except Exception as e:
#         logger.error(f"Error scheduling reminder tasks: {e}")

from celery import Celery
from datetime import datetime, time
import logging
from django.utils import timezone
from SubSync.models import Subscription
from SubSync.tasks import send_reminder_notification

logger = logging.getLogger(__name__)

# def schedule_reminder_tasks(subscription, reminder):
#     """Schedule tasks for all reminder dates."""
#     print("\n*************************************************************************************************************************************")

#     logger.info(f"Scheduling reminder tasks for reminder ID: {reminder.id}")

#     try:
#         # Stop scheduling tasks if the subscription is paid
#         # if subscription.payment_status == "Paid":
#         #     logger.info(f"Subscription ID {subscription.id} is paid. No reminders needed.")
#         #     return
        
#         reminder_dates = reminder.calculate_all_reminder_dates(subscription)
#         logger.info(f"Calculated reminder dates(in utils.py): {reminder_dates}")

#         task_ids = []  # List to store task IDs

#         for date in reminder_dates:
#             logger.info(f"Scheduling task for date: {date} at time: {DEFAULT_RENEWAL_TIME}")
#             # task_eta = datetime.combine(date, DEFAULT_RENEWAL_TIME)
#             task_eta = timezone.make_aware(datetime.combine(date, DEFAULT_RENEWAL_TIME))
#             logger.info(f"Scheduling reminder task for {task_eta}")
#             logger.info(f"Task ETA: {datetime.combine(date, DEFAULT_RENEWAL_TIME)}")

#             # send_reminder_notification.apply_async(
#             #     args=[reminder.id], eta=task_eta
#             # )
#             # send_reminder_notification.apply_async(
#             #     args=[reminder.id]
#             # )
#             # Schedule the task and store the task ID
#             task = send_reminder_notification.apply_async(args=[reminder.id])
#             task_ids.append(task.id)
        
#         reminder.scheduled_task_id = ",".join(task_ids)
#         reminder.save()

#     except Exception as e:
#         logger.error(f"Error scheduling reminder tasks: {e}")
DEFAULT_RENEWAL_TIME = time(12, 13, 0)

def schedule_reminder_tasks(entity, reminder):
    """Schedule tasks for all reminder dates."""
    print("\n**********************************************utils.py***************************************************************************************")
    
    logger.info(f"Scheduling reminder tasks for reminder ID: {reminder.id}")

    try:
        # Fetch user ID from the reminder
        user_id = entity.user.id if hasattr(entity, "user") else None 
        print("User ID:",user_id)

        # Determine if entity is a Subscription or Hardware
        entity_type = "Subscription" if isinstance(entity, Subscription) else "Hardware"
        logger.info(f"Scheduling reminders for {entity_type} ID: {entity.id} ")

        # Get reminder dates based on entity type
        reminder_dates = reminder.calculate_all_reminder_dates(entity)
        logger.info(f"Calculated reminder dates utils.py: {reminder_dates}")

        task_ids = []  # List to store task IDs

        for date in reminder_dates:
            # logger.info(f"Scheduling task for date: {date} at time: {DEFAULT_RENEWAL_TIME}")
            task_eta = timezone.make_aware(datetime.combine(date, DEFAULT_RENEWAL_TIME))
            # logger.info(f"Scheduling reminder task for {task_eta}")
            logger.info(f"Task ETA: {datetime.combine(date, DEFAULT_RENEWAL_TIME)}")

            # Schedule the task and store the task ID
            task = send_reminder_notification.apply_async(args=[reminder.id, user_id] ,task_eta=task_eta)
            task_ids.append(task.id)

        reminder.scheduled_task_id = ",".join(task_ids)
        reminder.save()

    except Exception as e:
        logger.error(f"Error scheduling reminder tasks: {e}")
