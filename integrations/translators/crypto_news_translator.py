import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from narratives.utils.random_sleep import random_sleep

class CryptoNewsTranslator:
    """
    A generic translator for crypto news sites.
    Uses site-specific selectors to extract full content from URLs.
    """
    
    # Map of source names to their content selectors
    SITE_CONFIG = {
        "theblock": {
            "selectors": [".article-content-container", "div#articleContent", ".article-content", ".articleBody", "article", "main"],
            "cleanup": ["Read More:", "Subscribe to our newsletter"]
        },
        "decrypt": {
            "selectors": [".post-content", ".article-body", "article", "main"],
            "cleanup": ["Read more:", "Decrypt"]
        },
        "cointelegraph": {
            "selectors": ["._html-renderer_mz5on_1", ".post-content", ".article-body", "article", "main"],
            "cleanup": ["Read more:", "Cointelegraph"]
        },
        "bitcoinmagazine": {
            "selectors": [".article-content", ".post-content", ".entry-content", "article", "main"],
            "cleanup": ["Read more:", "Subscribe", "Bitcoin Magazine"]
        },
        "beincrypto": {
            "selectors": [".article-content", ".post-content", ".entry-content", "article", "main"],
            "cleanup": ["Read more:", "BeInCrypto"]
        },
        "cryptoslate": {
            "selectors": [".article-content", ".post-content", ".entry-content", "article", "main"],
            "cleanup": ["Read more:", "CryptoSlate"]
        },
        "thedefiant": {
            "selectors": [".article-content", ".post-content", ".entry-content", "article", "main"],
            "cleanup": ["Read more:", "The Defiant"]
        },
        "blockworks": {
            "selectors": [".article-content", ".post-content", ".entry-content", "article", "main"],
            "cleanup": ["Read more:", "Blockworks"]
        },
    }

    def parse_articles(self, articles: List[Any], site_key: str) -> List[Dict[str, Any]]:
        rawtexts = []
        config = self.SITE_CONFIG.get(site_key, {})
        selectors = config.get("selectors", ["article", "main"])
        cleanup_markers = config.get("cleanup", [])

        for a in articles:
            full_content = a.summary
            paragraphs = []
            
            try:
                # Random sleep to avoid being blocked
                random_sleep(2, 6)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
                resp = requests.get(a.url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    content_div = None
                    for selector in selectors:
                        content_div = soup.select_one(selector)
                        if content_div:
                            break
                    
                    if content_div:
                        # Remove script and style tags
                        for script in content_div(["script", "style"]):
                            script.decompose()
                            
                        p_tags = content_div.find_all('p')
                        raw_paragraphs = [p.get_text().strip() for p in p_tags if p.get_text().strip()]
                        
                        # Clean up site-specific footers or ads
                        cleaned_paragraphs = []
                        skip_rest = False
                        for p in raw_paragraphs:
                            if skip_rest:
                                break
                            
                            lower_p = p.lower()
                            for marker in cleanup_markers:
                                if lower_p.startswith(marker.lower()):
                                    skip_rest = True
                                    break
                            
                            if not skip_rest:
                                cleaned_paragraphs.append(p)
                        
                        paragraphs = cleaned_paragraphs
                        if paragraphs:
                            full_content = "\n\n".join(paragraphs)
            except Exception as e:
                print(f"Failed to fetch full content for {a.url} ({site_key}): {e}")

            rawtexts.append({
                "title": a.title,
                "subtitle": None,
                "author": a.author or site_key.capitalize(),
                "content": full_content,
                "content_paragraphs": paragraphs,
                "published_at": a.published_at,
                "source_url": a.url,
                "genre": "news",
            })
        return rawtexts
