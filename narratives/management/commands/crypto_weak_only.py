"""
One-time: for all CRYPTO topics — remove Strong keywords, set Weak keywords only:
  !"TITLE" (name and alternative_name) with [CRYPTO_WEAK_CONTEXT], distance 3, both sides.
"""
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType


def make_weak_entry(keyword: str) -> dict:
    """Weak keyword in !\"TITLE\" form: whole word, case sensitive, crypto context, distance 3."""
    return {
        "keyword": keyword,
        "required_context": ["[CRYPTO_WEAK_CONTEXT]"],
        "distance": 3,
        "direction": "both",
        "requires_context": True,
        "whole_word_only": True,
        "case_sensitive": True,
    }


class Command(BaseCommand):
    help = "CRYPTO: remove strong keywords, set only weak !\"TITLE\" with [CRYPTO_WEAK_CONTEXT], distance 3"

    def handle(self, *args, **options):
        crypto_type = TopicType.objects.filter(name="CRYPTO").first()
        if not crypto_type:
            self.stdout.write(self.style.WARNING("No CRYPTO topic type found."))
            return

        qs = Topic.objects.filter(topic_type=crypto_type)
        total = qs.count()
        self.stdout.write(f"Found {total} CRYPTO topics. Applying weak-only setup...")

        updated = 0
        for topic in qs:
            weak = []
            name = (topic.name or "").strip()
            if name:
                weak.append(make_weak_entry(name))
            alt = (topic.alternative_name or "").strip()
            if alt and alt != name:
                weak.append(make_weak_entry(alt))

            if topic.keywords != [] or topic.weak_keywords != weak:
                topic.keywords = []
                topic.weak_keywords = weak
                topic.save(update_fields=["keywords", "weak_keywords"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} CRYPTO topics."))
