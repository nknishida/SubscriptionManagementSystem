from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class SubsyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SubSync'

    def ready(self):
        logger.info("Connecting signals...")
        import SubSync.signals

        try:
            from SubSync.tasks import setup_periodic_tasks
            setup_periodic_tasks()
            logger.info("Celery periodic tasks have been scheduled.")
        except Exception as e:
            logger.error(f"Error setting up periodic tasks: {e}")