import feedparser
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time
from bs4 import BeautifulSoup
from integrations.core.base_integration import IntegrationModule
from narratives.utils.random_sleep import random_sleep

@dataclass
class VitalikArticle:
    title: str
    url: str
    external_id: str
    published_at: Optional[datetime]
    summary: str
    content: str = ""

class VitalikScraper:
    def __init__(self, rss_url: str = "https://vitalik.eth.limo/feed.xml"):
        self.rss_url = rss_url

    def fetch_latest(self, limit: int = 10) -> List[VitalikArticle]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            print(f"DEBUG: Fetching RSS from {self.rss_url}")
            response = requests.get(self.rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            print(f"DEBUG: RSS fetched, entries: {len(feed.entries)}")
        except Exception as e:
            print(f"DEBUG: Error fetching RSS from {self.rss_url}: {e}")
            return []

        articles = []
        for entry in feed.entries[:limit]:
            published_at = None
            if hasattr(entry, 'published_parsed'):
                published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            
            # Vitalik's links in RSS are often vitalik.ca, we need to fix them
            link = entry.link.replace("vitalik.ca", "vitalik.eth.limo")
            # If the link doesn't have a protocol, add it
            if link.startswith("//"):
                link = "https:" + link
            elif not link.startswith("http"):
                link = "https://vitalik.eth.limo" + ("/" if not link.startswith("/") else "") + link
            
            external_id = getattr(entry, 'id', link)
            
            summary = entry.summary if hasattr(entry, 'summary') else ""
            
            article = VitalikArticle(
                title=entry.title,
                url=link,
                external_id=external_id,
                published_at=published_at,
                summary=summary
            )
            articles.append(article)
            
        return articles

class VitalikTranslator:
    def parse_articles(self, articles: List[VitalikArticle]) -> List[Dict[str, Any]]:
        rawtexts = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        for a in articles:
            full_content = a.summary
            
            # Vitalik's blog is very static and friendly, but let's be polite
            try:
                # The URL is already fixed in VitalikScraper.fetch_latest
                url = a.url
                print(f"DEBUG: Fetching full content from: {url}")
                random_sleep(1, 3)
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Vitalik's content is usually in a div with class 'content' or just inside the body
                    # Based on his current Jekyll setup:
                    content_div = soup.find('div', class_='content') or \
                                 soup.find('article') or \
                                 soup.find('div', class_='post') or \
                                 soup.find('div', class_='markdown-body')
                    
                    if content_div:
                        # Remove script and style tags
                        for s in content_div(['script', 'style']):
                            s.decompose()
                        
                        p_tags = content_div.find_all(['p', 'li', 'h1', 'h2', 'h3'])
                        paragraphs = [p.get_text().strip() for p in p_tags if p.get_text().strip()]
                        if paragraphs:
                            full_content = "\n\n".join(paragraphs)
                            print(f"DEBUG: Content extracted, length: {len(full_content)}")
                        else:
                            print("DEBUG: No paragraphs found in content_div")
                    else:
                        print("DEBUG: No content_div found")
                else:
                    print(f"DEBUG: Failed to fetch {url}, status: {resp.status_code}")
            except Exception as e:
                print(f"DEBUG: Failed to fetch full content for {a.url}: {e}")

            rawtexts.append({
                "title": a.title,
                "subtitle": "Vitalik Buterin's Blog",
                "author": "Vitalik Buterin",
                "content": full_content,
                "published_at": a.published_at,
                "source_url": a.url,
                "genre": "article",
            })
        return rawtexts

class VitalikIntegration(IntegrationModule):
    name = "VitalikIntegration"

    def fetch_content(self, source, source_config: dict) -> List[VitalikArticle]:
        rss_url = getattr(source, "rss_url", None) or "https://vitalik.eth.limo/feed.xml"
        limit = int(source_config.get("limit", 10))
        scraper = VitalikScraper(rss_url=rss_url)
        return scraper.fetch_latest(limit=limit)

    def normalize_to_rawtext(self, raw_data: List[VitalikArticle], source=None, source_config=None) -> List[Dict[str, Any]]:
        translator = VitalikTranslator()
        return translator.parse_articles(raw_data)
