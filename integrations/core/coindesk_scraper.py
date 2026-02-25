# integrations/core/coindesk_scraper.py
import datetime
import requests
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from .base_integration import IntegrationModule

class CoinDeskScraper(IntegrationModule):
    integration_slug = "coindesk"
    integration_name = "CoinDesk"
    resource_url = "https://www.coindesk.com/feed/"

    def fetch_content(self) -> str:
        response = requests.get(self.resource_url, timeout=15)
        response.raise_for_status()
        return response.text

    def normalize_to_rawtext(self, feed_xml: str) -> list[dict]:
        soup = BeautifulSoup(feed_xml, "xml")
        items = []
        for item in soup.find_all("item"):
            title = item.title.get_text(strip=True) if item.title else None
            link = item.link.get_text(strip=True) if item.link else None
            pub_date = item.pubDate.get_text(strip=True) if item.pubDate else None
            # RSS даты обычно RFC 2822 — парсим через email.utils
            published_at = (
                parsedate_to_datetime(pub_date).astimezone(datetime.timezone.utc)
                if pub_date
                else None
            )
            # полное содержание обычно находится в тегах description или content:encoded
            content_html = (
                item.find("content:encoded").get_text()
                if item.find("content:encoded")
                else item.description.get_text()
                if item.description
                else ""
            )
            content_soup = BeautifulSoup(content_html, "html.parser")
            content = content_soup.get_text(separator="\n").strip()
            items.append(
                {
                    "title": title,
                    "subtitle": None,
                    "content": content,
                    "source_url": link,
                    "author": None,
                    "published_at": published_at,
                }
            )
        return items