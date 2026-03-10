import logging
import random
import sys
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

MIN_DELAY_SEC = 30
MAX_DELAY_SEC = 300  # 5 min


def _gentle_fetcher_loop():
    """One fetch per source, then random sleep. Runs in background thread."""
    from django.db import connection
    from narratives.models import Source
    from django.db.models import Q
    from integrations.core.integration_registry import INTEGRATION_REGISTRY
    from integrations.run_integration import run_integration_for_source

    direct_slugs = [k for k in INTEGRATION_REGISTRY.keys() if k != "youtube"]
    while True:
        try:
            connection.close()  # use fresh connection per iteration
            sources = list(
                Source.objects.filter(
                    Q(platform="youtube") | Q(slug__in=direct_slugs)
                ).order_by("id")
            )
            if not sources:
                time.sleep(60)
                continue
            for source in sources:
                try:
                    count, _ = run_integration_for_source(
                        source, limit=1, mark_all_not_new=False
                    )
                    if count:
                        logger.info("Gentle fetcher: %s imported %s", source.name, count)
                except Exception as e:
                    logger.warning("Gentle fetcher %s: %s", source.name, e)
                sec = random.randint(MIN_DELAY_SEC, MAX_DELAY_SEC)
                time.sleep(sec)
        except Exception as e:
            logger.exception("Gentle fetcher loop: %s", e)
            time.sleep(60)


class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations'

    def ready(self):
        from django.conf import settings
        # Only start fetcher when running the web server (not migrate, shell, etc.)
        run_web = "runserver" in sys.argv or "gunicorn" in sys.argv[0].lower()
        if run_web and getattr(settings, "GENTLE_FETCHER_AUTO_START", True):
            thread = threading.Thread(target=_gentle_fetcher_loop, daemon=True)
            thread.start()
            logger.info("Gentle fetcher background thread started.")
