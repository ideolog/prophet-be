# narratives/management/commands/add_direct_sources.py
"""Add Direct/RSS sources for crypto news (slug must match INTEGRATION_REGISTRY)."""

from django.core.management.base import BaseCommand
from narratives.models import Source


DIRECT_SOURCES = [
    {
        "name": "Bitcoin Magazine",
        "slug": "bitcoinmagazine",
        "url": "https://bitcoinmagazine.com/",
        "rss_url": "https://bitcoinmagazine.com/feed",
        "platform": "direct",
    },
    {
        "name": "BeInCrypto",
        "slug": "beincrypto",
        "url": "https://beincrypto.com/",
        "rss_url": "https://beincrypto.com/feed/",
        "platform": "direct",
    },
    {
        "name": "CryptoSlate",
        "slug": "cryptoslate",
        "url": "https://cryptoslate.com/",
        "rss_url": "https://cryptoslate.com/feed/",
        "platform": "direct",
    },
    {
        "name": "The Defiant",
        "slug": "thedefiant",
        "url": "https://thedefiant.io/",
        "rss_url": "https://thedefiant.io/feed",
        "platform": "direct",
    },
    {
        "name": "Blockworks",
        "slug": "blockworks",
        "url": "https://blockworks.co/",
        "rss_url": "https://blockworks.co/feed",
        "platform": "direct",
    },
    {
        "name": "CryptoPotato",
        "slug": "cryptopotato",
        "url": "https://cryptopotato.com/",
        "rss_url": "https://cryptopotato.com/feed/",
        "platform": "direct",
    },
    {
        "name": "U.Today",
        "slug": "utoday",
        "url": "https://u.today/",
        "rss_url": "https://u.today/rss",
        "platform": "direct",
    },
    {
        "name": "CoinJournal",
        "slug": "coinjournal",
        "url": "https://coinjournal.net/",
        "rss_url": "https://coinjournal.net/news/feed/",
        "platform": "direct",
    },
    {
        "name": "NewsBTC",
        "slug": "newsbtc",
        "url": "https://www.newsbtc.com/",
        "rss_url": "https://www.newsbtc.com/feed/",
        "platform": "direct",
    },
    {
        "name": "CryptoNews",
        "slug": "cryptonews",
        "url": "https://cryptonews.com/",
        "rss_url": "https://cryptonews.com/news/feed/",
        "platform": "direct",
    },
]


class Command(BaseCommand):
    help = "Add Direct/RSS sources (Bitcoin Magazine, BeInCrypto, CryptoSlate, The Defiant, Blockworks, CryptoPotato, U.Today, CoinJournal, NewsBTC, CryptoNews)"

    def handle(self, *args, **options):
        for src in DIRECT_SOURCES:
            obj, created = Source.objects.get_or_create(
                slug=src["slug"],
                defaults={
                    "name": src["name"],
                    "url": src.get("url"),
                    "rss_url": src.get("rss_url"),
                    "platform": src.get("platform", "direct"),
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added: {src['name']} ({src['slug']})"))
            else:
                if obj.rss_url != src.get("rss_url"):
                    obj.rss_url = src.get("rss_url")
                    obj.save()
                    self.stdout.write(self.style.WARNING(f"Updated rss_url for: {src['name']}"))
                else:
                    self.stdout.write(f"Already exists: {src['name']}")
        self.stdout.write(self.style.SUCCESS("Done."))
