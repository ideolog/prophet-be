import feedparser
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time
from integrations.core.base_integration import IntegrationModule
from integrations.translators.coindesk_translator import CoinDeskTranslator

@dataclass
class CoinDeskArticle:
    title: str
    url: str
    external_id: str
    published_at: Optional[datetime]
    author: Optional[str]
    summary: str
    content: str = ""

class CoinDeskScraper:
    def __init__(self, rss_url: str):
        self.rss_url = rss_url

    def fetch_latest(self, limit: int = 10) -> List[CoinDeskArticle]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.get(self.rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Error fetching RSS from {self.rss_url}: {e}")
            return []

        articles = []
        
        for entry in feed.entries[:limit]:
            published_at = None
            if hasattr(entry, 'published_parsed'):
                published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            
            # CoinDesk RSS usually has id or link
            external_id = getattr(entry, 'id', entry.link)
            
            article = CoinDeskArticle(
                title=entry.title,
                url=entry.link,
                external_id=external_id,
                published_at=published_at,
                author=getattr(entry, 'author', None),
                summary=entry.summary if hasattr(entry, 'summary') else ""
            )
            articles.append(article)
            
        return articles

class CoinDeskIntegration(IntegrationModule):
    """
    Integration contract:
    - fetch_content(source, source_config) -> raw payload (any)
    - normalize_to_rawtext(raw_payload, source, source_config) -> list[dict]
    """
    name = "CoinDeskIntegration"

    def fetch_content(self, source, source_config: dict) -> List[CoinDeskArticle]:
        # RSS URL must be stored on the Source model (DB), not passed via request payload.
        rss_url = (
            getattr(source, "rss_url", None)
            or getattr(source, "feed_url", None)
            or getattr(source, "url", None)
        )

        if not rss_url:
            # Fallback to default CoinDesk RSS if not configured
            rss_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"

        limit = int(source_config.get("limit", 10))

        scraper = CoinDeskScraper(rss_url=rss_url)
        return scraper.fetch_latest(limit=limit)

    def normalize_to_rawtext(
        self,
        raw_data: List[CoinDeskArticle],
        source=None,
        source_config=None,
    ) -> List[Dict[str, Any]]:
        translator = CoinDeskTranslator()
        return translator.parse_articles(raw_data)
