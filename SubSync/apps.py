from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class SubsyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SubSync'

def ready(self):
    logger.info("Connecting signals...")
    import SubSync.signals
