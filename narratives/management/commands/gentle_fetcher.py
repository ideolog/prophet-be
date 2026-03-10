# narratives/management/commands/gentle_fetcher.py
"""Background fetcher: one video per YouTube channel, one article per direct/RSS source, with random 30s–5min delay between each."""

import random
import time
from django.core.management.base import BaseCommand
from django.db.models import Q

from narratives.models import Source
from integrations.core.integration_registry import INTEGRATION_REGISTRY
from integrations.run_integration import run_integration_for_source


MIN_DELAY_SEC = 30
MAX_DELAY_SEC = 300  # 5 minutes


def get_fetchable_sources():
    """YouTube sources + direct/RSS sources that have a registered integration (by slug)."""
    direct_slugs = [k for k in INTEGRATION_REGISTRY.keys() if k != "youtube"]
    return list(
        Source.objects.filter(
            Q(platform="youtube") | Q(slug__in=direct_slugs)
        ).order_by("id")
    )


def random_sleep():
    sec = random.randint(MIN_DELAY_SEC, MAX_DELAY_SEC)
    time.sleep(sec)
    return sec


class Command(BaseCommand):
    help = "Run gentle background fetcher: 1 video/channel, 1 article/source, random 30s–5min between each."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run one full round (one fetch per source) then exit",
        )
        parser.add_argument(
            "--min-delay",
            type=int,
            default=MIN_DELAY_SEC,
            help=f"Min delay between fetches in seconds (default {MIN_DELAY_SEC})",
        )
        parser.add_argument(
            "--max-delay",
            type=int,
            default=MAX_DELAY_SEC,
            help=f"Max delay between fetches in seconds (default {MAX_DELAY_SEC})",
        )

    def handle(self, *args, **options):
        run_once = options.get("once", False)
        min_delay = max(1, options.get("min_delay", MIN_DELAY_SEC))
        max_delay = max(min_delay, options.get("max_delay", MAX_DELAY_SEC))

        def delay_sec():
            return random.randint(min_delay, max_delay)

        sources = get_fetchable_sources()
        if not sources:
            self.stdout.write(self.style.WARNING("No fetchable sources found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Gentle fetcher started. {len(sources)} sources. Delay {min_delay}s–{max_delay}s between fetches."))

        round_num = 0
        while True:
            round_num += 1
            self.stdout.write(f"Round {round_num}: fetching one item per source…")
            for source in sources:
                try:
                    count, ids = run_integration_for_source(source, limit=1, mark_all_not_new=False)
                    if count:
                        self.stdout.write(self.style.SUCCESS(f"  {source.name} (slug={source.slug}): imported {count}"))
                    else:
                        self.stdout.write(f"  {source.name}: no new items")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  {source.name}: {e}"))
                sec = delay_sec()
                self.stdout.write(f"  sleeping {sec}s…")
                time.sleep(sec)

            if run_once:
                self.stdout.write(self.style.SUCCESS("One round done (--once). Exiting."))
                return
            self.stdout.write("Starting next round…")
