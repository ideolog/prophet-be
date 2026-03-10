"""
Fetch cryptocurrencies from CoinGecko (by market cap) and create/update CRYPTO topics.
Free API rate limit: run occasionally (e.g. daily). If 0 coins, wait a few minutes and re-run.
Adds weak keyword for alternative_name with [CRYPTO_WEAK_CONTEXT] (distance 5, whole word, case sensitive).
"""
from django.core.management.base import BaseCommand
from narratives.models import Topic, TopicType
from integrations.coingecko import fetch_coins_by_market_cap

CRYPTO_WEAK_ENTRY = {
    "keyword": None,  # set to alternative_name per topic
    "required_context": ["[CRYPTO_WEAK_CONTEXT]"],
    "distance": 5,
    "direction": "both",
    "requires_context": True,
    "whole_word_only": True,
    "case_sensitive": True,
}


def ensure_crypto_weak_keyword(topic: Topic) -> None:
    """Ensure topic has weak keyword for alternative_name with CRYPTO_WEAK_CONTEXT. Idempotent."""
    alt = (topic.alternative_name or "").strip()
    if not alt:
        return
    entry = {**CRYPTO_WEAK_ENTRY, "keyword": alt}
    weak = list(topic.weak_keywords or [])
    found = False
    for i, w in enumerate(weak):
        if isinstance(w, dict) and w.get("keyword") == alt and "[CRYPTO_WEAK_CONTEXT]" in (w.get("required_context") or []):
            weak[i] = entry
            found = True
            break
    if not found:
        weak.append(entry)
    topic.weak_keywords = weak
    topic.save(update_fields=["weak_keywords"])


class Command(BaseCommand):
    help = "Sync CRYPTO topics from CoinGecko API (by market cap)"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=4, help="Max API pages (250 coins each)")
        parser.add_argument("--delay", type=float, default=5.0, help="Seconds between pages")

    def handle(self, *args, **options):
        max_pages = options["pages"]
        delay = options["delay"]

        crypto_type, _ = TopicType.objects.get_or_create(
            name="CRYPTO",
            defaults={"description": "Cryptocurrency (by ticker/symbol)"},
        )

        self.stdout.write("Fetching from CoinGecko (market_cap_desc)...")
        try:
            coins = fetch_coins_by_market_cap(
                per_page=250, max_pages=max_pages, delay_seconds=delay
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fetch failed: {e}"))
            return

        if not coins:
            self.stdout.write(
                self.style.WARNING(
                    "No coins received (rate limit?). Wait a few minutes and run again."
                )
            )
            return

        self.stdout.write(f"Received {len(coins)} coins. Upserting...")
        created = 0
        updated = 0

        for c in coins:
            ticker = c["symbol"]
            name = c["name"]
            keyword_spec = {
                "keyword": ticker,
                "whole_word_only": True,
                "case_sensitive": True,
            }

            topic = Topic.objects.filter(name=ticker).first()
            if not topic:
                topic = Topic.objects.filter(alternative_name__iexact=name).first()
            if topic:
                topic.alternative_name = name
                topic.topic_type = crypto_type
                has_kw = any(
                    isinstance(k, dict)
                    and k.get("keyword") == ticker
                    and k.get("case_sensitive")
                    for k in (topic.keywords or [])
                )
                if not has_kw:
                    topic.keywords = (topic.keywords or []) + [keyword_spec]
                topic.save()
                ensure_crypto_weak_keyword(topic)
                updated += 1
            else:
                topic = Topic.objects.create(
                    name=ticker,
                    alternative_name=name,
                    topic_type=crypto_type,
                    keywords=[keyword_spec],
                    weak_keywords=[],
                )
                ensure_crypto_weak_keyword(topic)
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created: {created}, Updated: {updated}")
        )
