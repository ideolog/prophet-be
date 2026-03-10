import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from narratives.utils.random_sleep import random_sleep

class CoinDeskTranslator:
    def parse_articles(self, articles: List[Any]) -> List[Dict[str, Any]]:
        rawtexts = []
        for a in articles:
            # If content is empty, we might want to fetch full content from URL
            # CoinDesk RSS often only has summary
            full_content = a.summary
            paragraphs = []
            
            # Optional: Fetch full content if summary is too short or if we want full text
            # For now, let's implement a basic full text fetcher
            try:
                random_sleep(2, 5)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                resp = requests.get(a.url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # CoinDesk article content is usually in specific classes
                    # This might need adjustment based on their current HTML structure
                    content_div = soup.find('div', class_='article-body') or \
                                 soup.find('div', class_='at-body') or \
                                 soup.find('article') or \
                                 soup.find('main')
                    
                    if content_div:
                        p_tags = content_div.find_all('p')
                        paragraphs = [p.get_text().strip() for p in p_tags if p.get_text().strip()]
                        
                        # Clean up CoinDesk specific "Read More" and "More For You" sections
                        cleaned_paragraphs = []
                        skip_rest = False
                        for p in paragraphs:
                            if skip_rest:
                                break
                            
                            # Check for common CoinDesk footer markers
                            lower_p = p.lower()
                            if lower_p.startswith("read more:") or \
                               lower_p == "more for you" or \
                               lower_p == "what to know:":
                                skip_rest = True
                                continue
                            
                            cleaned_paragraphs.append(p)
                        
                        paragraphs = cleaned_paragraphs
                        if paragraphs:
                            full_content = "\n\n".join(paragraphs)
            except Exception as e:
                print(f"Failed to fetch full content for {a.url}: {e}")

            rawtexts.append({
                "title": a.title,
                "subtitle": None,
                "author": a.author or "CoinDesk",
                "content": full_content,
                "content_paragraphs": paragraphs,
                "published_at": a.published_at,
                "source_url": a.url,
                "genre": "news",
            })
        return rawtexts
