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


class BitcoinMagazineIntegration(BaseCryptoIntegration):
    name = "BitcoinMagazineIntegration"
    site_key = "bitcoinmagazine"
    default_rss = "https://bitcoinmagazine.com/feed"


class BeInCryptoIntegration(BaseCryptoIntegration):
    name = "BeInCryptoIntegration"
    site_key = "beincrypto"
    default_rss = "https://beincrypto.com/feed/"


class CryptoSlateIntegration(BaseCryptoIntegration):
    name = "CryptoSlateIntegration"
    site_key = "cryptoslate"
    default_rss = "https://cryptoslate.com/feed/"


class TheDefiantIntegration(BaseCryptoIntegration):
    name = "TheDefiantIntegration"
    site_key = "thedefiant"
    default_rss = "https://thedefiant.io/feed"


class BlockworksIntegration(BaseCryptoIntegration):
    name = "BlockworksIntegration"
    site_key = "blockworks"
    default_rss = "https://blockworks.co/feed"


class CryptoPotatoIntegration(BaseCryptoIntegration):
    name = "CryptoPotatoIntegration"
    site_key = "cryptopotato"
    default_rss = "https://cryptopotato.com/feed/"


class UTodayIntegration(BaseCryptoIntegration):
    name = "UTodayIntegration"
    site_key = "utoday"
    default_rss = "https://u.today/rss"


class CoinJournalIntegration(BaseCryptoIntegration):
    name = "CoinJournalIntegration"
    site_key = "coinjournal"
    default_rss = "https://coinjournal.net/news/feed/"


class NewsBTCIntegration(BaseCryptoIntegration):
    name = "NewsBTCIntegration"
    site_key = "newsbtc"
    default_rss = "https://www.newsbtc.com/feed/"


class CryptoNewsIntegration(BaseCryptoIntegration):
    name = "CryptoNewsIntegration"
    site_key = "cryptonews"
    default_rss = "https://cryptonews.com/news/feed/"
