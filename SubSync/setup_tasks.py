from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

def setup_periodic_tasks():
    """Automatically create/update periodic tasks in django-celery-beat."""
    
    # Schedule for updating subscription status (Runs every 1 hour)
    schedule_1, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    # schedule_1, _ = IntervalSchedule.objects.get_or_create(
    # every=5, period=IntervalSchedule.MINUTES  # Change HOURS → MINUTES
    # )
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
            "task": "SubSync.tasks.update_customer_status",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    schedule_clean, _ = IntervalSchedule.objects.get_or_create(
    every=30, period=IntervalSchedule.DAYS
    )
    PeriodicTask.objects.update_or_create(
        name="Clean Old History",
        defaults={
            "interval": schedule_clean,
            "task": "SubSync.tasks.clean_old_history",
            "kwargs": json.dumps({"days_to_keep": 90})  # Keep 3 months history
        }
    )

    schedule_5, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="Update hardware service Status",
        defaults={
            "interval": schedule_5,
            "task": "SubSync.tasks.update_hardware_service_statuses",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    schedule_6, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="subscription reminder",
        defaults={
            "interval": schedule_6,
            "task": "SubSync.tasks.send_due_reminders",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    schedule_7, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="hardware reminder",
        defaults={
            "interval": schedule_7,
            "task": "SubSync.tasks.send_hardware_reminders",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    schedule_8, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.HOURS
    )
    PeriodicTask.objects.update_or_create(
        name="customer reminder",
        defaults={
            "interval": schedule_8,
            "task": "SubSync.tasks.send_customer_reminders",
            "args": json.dumps([]),
            "kwargs": json.dumps({})
        }
    )

    # schedule_9, _ = IntervalSchedule.objects.get_or_create(
    #     every=5, period=IntervalSchedule.MINUTES
    # )
    # PeriodicTask.objects.update_or_create(
    #     name="hardware reminder",
    #     defaults={
    #         "interval": schedule_9,
    #         "task": "SubSync.tasks.send_hardware_reminders",
    #         "args": json.dumps([]),
    #         "kwargs": json.dumps({})
    #     }
    # )
    
    print("Periodic tasks have been set up successfully!")