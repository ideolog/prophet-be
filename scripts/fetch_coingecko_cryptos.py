"""
Fetch cryptocurrencies from CoinGecko API (by market cap) and create/update Topic with type CRYPTO.
- Topic name = ticker (symbol, e.g. BTC)
- Alternative name = full name (e.g. Bitcoin)
- Strong keyword = case-sensitive whole word !"TICKER"
Uses free CoinGecko API; rate limit ~10-30 req/min. Fetches up to 1000 coins (4 pages x 250).
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prophet_be.settings")
django.setup()

from narratives.models import Topic, TopicType
from integrations.coingecko import fetch_coins_by_market_cap


def main():
    crypto_type, _ = TopicType.objects.get_or_create(
        name="CRYPTO",
        defaults={"description": "Cryptocurrency (by ticker/symbol)"},
    )

    print("Fetching from CoinGecko (market_cap_desc)...")
    try:
        coins = fetch_coins_by_market_cap(per_page=250, max_pages=4, delay_seconds=5.0)
    except Exception as e:
        print(f"Fetch failed: {e}")
        return
    if not coins:
        print("No coins received.")
        return

    print(f"Received {len(coins)} coins. Upserting...")

    created = 0
    updated = 0
    skipped = 0

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
                isinstance(k, dict) and k.get("keyword") == ticker and k.get("case_sensitive")
                for k in (topic.keywords or [])
            )
            if not has_kw:
                topic.keywords = (topic.keywords or []) + [keyword_spec]
            topic.save()
            updated += 1
        else:
            Topic.objects.create(
                name=ticker,
                alternative_name=name,
                topic_type=crypto_type,
                keywords=[keyword_spec],
            )
            created += 1

    print(f"Done. Created: {created}, Updated: {updated}")


if __name__ == "__main__":
    main()
