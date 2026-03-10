"""
Import cryptocurrencies from data/csv/top_100_cryptocurrencies.csv.
- TopicType CRYPTO is created if missing.
- Each row: "Full Name (TICKER)" -> Topic name=TICKER, alternative_name=Full Name,
  topic_type=CRYPTO, keywords=[!"TICKER"] (case-sensitive whole word).
- If topic exists (by name or alt), update it; otherwise create.
"""
import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prophet_be.settings")
django.setup()

from narratives.models import Topic, TopicType

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "csv", "top_100_cryptocurrencies.csv")


def parse_line(line: str) -> tuple[str, str] | None:
    """Return (full_name, ticker). Ticker = last parenthesized token if it looks like SYMBOL else part before first '('."""
    line = line.strip()
    if not line or line == "Cryptocurrency":
        return None
    r = line.rfind("(")
    if r == -1:
        return None
    rr = line.find(")", r)
    if rr == -1:
        return None
    in_parens = line[r + 1 : rr].strip()
    full_name = line[:r].strip()
    # If parenthesized part looks like a ticker (e.g. BTC, USDT), use it; else use text before " (" (e.g. POL (ex-MATIC) -> POL)
    if in_parens and re.match(r"^[A-Z0-9]{2,15}$", in_parens, re.IGNORECASE) and "ex-" not in in_parens:
        ticker = in_parens.upper()
    else:
        ticker = full_name.strip().upper()
    if not ticker or not full_name:
        return None
    return (full_name, ticker)


def main():
    if not os.path.isfile(CSV_PATH):
        print(f"File not found: {CSV_PATH}")
        return

    crypto_type, created = TopicType.objects.get_or_create(
        name="CRYPTO",
        defaults={"description": "Cryptocurrency (by ticker/symbol)"},
    )
    if created:
        print("Created TopicType: CRYPTO")

    seen_tickers = set()
    created_count = 0
    updated_count = 0

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if not parsed:
                continue
            full_name, ticker = parsed
            if ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)

            keyword_spec = {
                "keyword": ticker,
                "whole_word_only": True,
                "case_sensitive": True,
            }

            topic = Topic.objects.filter(name=ticker).first()
            if not topic:
                topic = Topic.objects.filter(alternative_name__iexact=full_name).first()
            if topic:
                topic.alternative_name = full_name
                topic.topic_type = crypto_type
                if not any(
                    isinstance(k, dict) and k.get("keyword") == ticker and k.get("case_sensitive")
                    for k in (topic.keywords or [])
                ):
                    topic.keywords = (topic.keywords or []) + [keyword_spec]
                topic.save()
                updated_count += 1
                print(f"  Updated: {ticker} ({full_name})")
            else:
                Topic.objects.create(
                    name=ticker,
                    alternative_name=full_name,
                    topic_type=crypto_type,
                    keywords=[keyword_spec],
                )
                created_count += 1
                print(f"  Created: {ticker} ({full_name})")

    print(f"\nDone. Created: {created_count}, Updated: {updated_count}")


if __name__ == "__main__":
    main()
