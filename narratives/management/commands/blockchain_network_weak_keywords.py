"""
One-time: for all topics with type "Blockchain network" — add weak keyword from title
(name minus " network") in quotes with [BLOCKCHAIN_NETWORK], distance 5, both sides.
Does not remove existing keywords or other weak keywords.
"""
import re
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType


def extract_blockchain_name(name: str) -> str:
    """Strip and remove trailing ' network' / ' Network' (case insensitive)."""
    if not name:
        return ""
    s = name.strip()
    if not s:
        return ""
    # Remove suffix " network" (case insensitive)
    if re.search(r"\s+network\s*$", s, re.IGNORECASE):
        s = re.sub(r"\s+network\s*$", "", s, flags=re.IGNORECASE).strip()
    return s


def make_weak_entry(keyword: str) -> dict:
    """Weak keyword in quotes: whole word, not case sensitive, [BLOCKCHAIN_NETWORK], distance 5."""
    return {
        "keyword": keyword,
        "required_context": ["[BLOCKCHAIN_NETWORK]"],
        "distance": 5,
        "direction": "both",
        "requires_context": True,
        "whole_word_only": True,
        "case_sensitive": False,
    }


class Command(BaseCommand):
    help = 'Blockchain network: add weak keyword from title (name minus " network") with [BLOCKCHAIN_NETWORK], distance 5'

    def handle(self, *args, **options):
        bn_type = TopicType.objects.filter(name__iexact="Blockchain network").first()
        if not bn_type:
            self.stdout.write(self.style.WARNING('TopicType "Blockchain network" not found.'))
            return

        qs = Topic.objects.filter(topic_type=bn_type)
        total = qs.count()
        self.stdout.write(f"Found {total} topics with type Blockchain network.")

        updated = 0
        for topic in qs:
            main_word = extract_blockchain_name(topic.name or "")
            if not main_word:
                continue

            entry = make_weak_entry(main_word)
            weak = list(topic.weak_keywords or [])
            found_idx = None
            for i, w in enumerate(weak):
                if not isinstance(w, dict):
                    continue
                if (w.get("keyword") or "").strip() != main_word:
                    continue
                req = w.get("required_context") or []
                if "[BLOCKCHAIN_NETWORK]" not in req and "[blockchain_network]" not in [str(x).lower() for x in req]:
                    continue
                found_idx = i
                break

            if found_idx is not None:
                weak[found_idx] = entry
            else:
                weak.append(entry)

            topic.weak_keywords = weak
            topic.save(update_fields=["weak_keywords"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} topics."))
