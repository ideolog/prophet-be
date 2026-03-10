"""
CoinGecko free API integration: fetch list of cryptocurrencies by market cap.
No API key required. Free tier: ~10-30 req/min; use sparingly (e.g. daily sync).
Docs: https://www.coingecko.com/api/documentations/v3
"""
import time
import requests

BASE_URL = "https://api.coingecko.com/api/v3/coins/markets"


def fetch_coins_page(
    page: int = 1,
    per_page: int = 250,
    vs_currency: str = "usd",
) -> list[dict]:
    """
    Fetch one page of coins by market_cap_desc. Returns list of {symbol, name, market_cap_rank, id}.
    Raises on HTTP error (e.g. 429). Caller should delay between pages.
    """
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
    }
    headers = {"User-Agent": "ProphetOntology/1.0 (crypto list sync)"}
    r = requests.get(BASE_URL, params=params, timeout=30, headers=headers)
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data:
        symbol = (item.get("symbol") or "").strip().upper()
        name = (item.get("name") or "").strip()
        if symbol and name:
            results.append({
                "symbol": symbol,
                "name": name,
                "market_cap_rank": item.get("market_cap_rank"),
                "id": item.get("id"),
            })
    return results


def fetch_coins_by_market_cap(
    vs_currency: str = "usd",
    per_page: int = 250,
    max_pages: int = 4,
    delay_seconds: float = 2.0,
) -> list[dict]:
    """
    Fetch coins ordered by market_cap_desc. Returns list of {symbol, name, market_cap_rank, id}.
    Stops on 429 or error; returns whatever was fetched so far.
    """
    results = []
    for page in range(1, max_pages + 1):
        try:
            data = fetch_coins_page(page=page, per_page=per_page, vs_currency=vs_currency)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                break  # rate limited, return what we have
            raise RuntimeError(f"CoinGecko API error (page {page}): {e}") from e
        except Exception as e:
            raise RuntimeError(f"CoinGecko API error (page {page}): {e}") from e

        results.extend(data)
        if len(data) < per_page:
            break
        if page < max_pages:
            time.sleep(delay_seconds)

    return results
