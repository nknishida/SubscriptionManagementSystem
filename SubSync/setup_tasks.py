from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

def setup_periodic_tasks():
    """Automatically create/update periodic tasks in django-celery-beat."""
    
    # Schedule for updating subscription status (Runs every 1 hour)
    # schedule_1, _ = IntervalSchedule.objects.get_or_create(
    #     every=1, period=IntervalSchedule.HOURS
    # )
    schedule_1, _ = IntervalSchedule.objects.get_or_create(
    every=5, period=IntervalSchedule.MINUTES  # Change HOURS → MINUTES
    )
    PeriodicTask.objects.update_or_create(
        name="Update Subscription Status",
        defaults={
            "interval": schedule_1,
            "task": "SubSync.tasks.update_subscriptions_status",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    # Schedule for deleting old recycle bin items (Runs every 24 hours)
    schedule_2, _ = IntervalSchedule.objects.get_or_create(
        every=24, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="Delete Old Recycle Bin Items",
        defaults={
            "interval": schedule_2,
            "task": "SubSync.tasks.delete_old_recycle_bin_items",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )
    
    # Schedule for updating warranty status (Runs every 24 hours)
    schedule_3, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="Update Warranty Status",
        defaults={
            "interval": schedule_3,
            "task": "SubSync.tasks.update_warranty_status",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    # Schedule for updating customer status (Runs every 24 hours)
    schedule_4, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="Update Customer Status",
        defaults={
            "interval": schedule_4,
            "task": "SubSync.tasks.update_customers_status",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    print("Periodic tasks have been set up successfully!")
