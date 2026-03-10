"""
One-time backfill: for every Topic with type CRYPTO and non-empty alternative_name,
add weak keyword (alternative_name + [CRYPTO_WEAK_CONTEXT], distance 5) if not already present.
"""
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType
from narratives.management.commands.sync_coingecko_cryptos import ensure_crypto_weak_keyword


class Command(BaseCommand):
    help = "Add CRYPTO weak keyword (alt name + CRYPTO_WEAK_CONTEXT) to existing CRYPTO topics"

    def handle(self, *args, **options):
        crypto_type = TopicType.objects.filter(name="CRYPTO").first()
        if not crypto_type:
            self.stdout.write(self.style.WARNING("No CRYPTO topic type found. Run sync_coingecko_cryptos first."))
            return
        qs = Topic.objects.filter(topic_type=crypto_type).exclude(alternative_name__isnull=True).exclude(alternative_name="")
        total = qs.count()
        self.stdout.write(f"Found {total} CRYPTO topics with alternative_name.")
        done = 0
        for topic in qs:
            ensure_crypto_weak_keyword(topic)
            done += 1
        self.stdout.write(self.style.SUCCESS(f"Done. Ensured weak keyword on {done} topics."))
