import feedparser
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time
from integrations.core.base_integration import IntegrationModule
from integrations.translators.crypto_news_translator import CryptoNewsTranslator

@dataclass
class CryptoArticle:
    title: str
    url: str
    external_id: str
    published_at: Optional[datetime]
    author: Optional[str]
    summary: str
    content: str = ""

class CryptoRSSScraper:
    def __init__(self, rss_url: str):
        self.rss_url = rss_url

    def fetch_latest(self, limit: int = 10) -> List[CryptoArticle]:
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
            elif hasattr(entry, 'updated_parsed'):
                published_at = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
            external_id = getattr(entry, 'id', entry.link)
            
            summary = ""
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description

            article = CryptoArticle(
                title=entry.title,
                url=entry.link,
                external_id=external_id,
                published_at=published_at,
                author=getattr(entry, 'author', None),
                summary=summary
            )
            articles.append(article)
            
        return articles

class BaseCryptoIntegration(IntegrationModule):
    site_key = ""
    default_rss = ""

    def fetch_content(self, source, source_config: dict) -> List[CryptoArticle]:
        rss_url = (
            getattr(source, "rss_url", None)
            or getattr(source, "feed_url", None)
            or getattr(source, "url", None)
        )

        if not rss_url:
            rss_url = self.default_rss

        limit = int(source_config.get("limit", 10))
        scraper = CryptoRSSScraper(rss_url=rss_url)
        return scraper.fetch_latest(limit=limit)

    def normalize_to_rawtext(
        self,
        raw_data: List[CryptoArticle],
        source=None,
        source_config=None,
    ) -> List[Dict[str, Any]]:
        translator = CryptoNewsTranslator()
        return translator.parse_articles(raw_data, self.site_key)

class TheBlockIntegration(BaseCryptoIntegration):
    name = "TheBlockIntegration"
    site_key = "theblock"
    default_rss = "https://www.theblock.co/rss.xml"

class DecryptIntegration(BaseCryptoIntegration):
    name = "DecryptIntegration"
    site_key = "decrypt"
    default_rss = "https://decrypt.co/feed"

class CoinTelegraphIntegration(BaseCryptoIntegration):
    name = "CoinTelegraphIntegration"
    site_key = "cointelegraph"
    default_rss = "https://cointelegraph.com/rss"
