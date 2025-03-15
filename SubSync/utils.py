from datetime import datetime, time, timedelta, timezone
from dateutil.relativedelta import relativedelta
from celery import Celery
from SubSync.tasks import send_reminder_email
from .models import Reminder
import logging
logger = logging.getLogger(__name__)

DEFAULT_RENEWAL_TIME = time(13, 15, 0)
# DEFAULT_RENEWAL_TIME = "16:00:00"

def schedule_reminder_tasks(subscription, reminder):
    """Schedule tasks for all reminder dates."""
    logger.info(f"Entering schedule_reminder_tasks for reminder ID: {reminder.id}")
    
    try:
        reminder_dates = reminder.calculate_all_reminder_dates(subscription)
        logger.info(f"Scheduling tasks for reminder ID: {reminder.id}")
        logger.info(f"Calculated reminder dates: {reminder_dates}")
        
        for date in reminder_dates:
            # logger.info(f"Scheduling task for date: {date} at time: {reminder.reminder_time}")
            logger.info(f"Scheduling task for date: {date} at time: DEFAULT_RENEWAL_TIME")
            # Schedule the task to run on the reminder date at the reminder time
            # send_reminder_email.apply_async(args=[reminder.id], eta=timezone.datetime.combine(date, reminder.reminder_time))
            
            logger.info(f"Task ETA: {datetime.combine(date, DEFAULT_RENEWAL_TIME)}")
            send_reminder_email.apply_async(
                args=[reminder.id], 
                eta=datetime.combine(date, DEFAULT_RENEWAL_TIME)
            )

    except Exception as e:
        logger.error(f"Error scheduling reminder tasks: {e}")