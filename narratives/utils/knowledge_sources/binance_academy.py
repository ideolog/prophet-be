import requests
from bs4 import BeautifulSoup
import re

def fetch_binance_academy(topic_name: str):
    """
    Attempts to fetch a definition from Binance Academy Glossary.
    """
    # Binance uses a slug-based URL for glossary terms
    slug = topic_name.lower().replace(" ", "-")
    url = f"https://academy.binance.com/en/glossary/{slug}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Binance Academy structure often has the definition in a specific div or meta tag
        # Let's try to find the main content
        content_div = soup.find('div', {'class': re.compile(r'.*description.*')}) or \
                      soup.find('article')
        
        if not content_div:
            # Fallback: check meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            content = meta_desc['content'] if meta_desc else ""
        else:
            content = content_div.get_text(separator=' ', strip=True)

        if len(content) < 50: # Too short to be a useful definition
            return None

        return {
            "source": "Binance Academy",
            "title": topic_name,
            "content": content[:2000],
            "url": url
        }
    except Exception as e:
        print(f"Error fetching from Binance Academy: {e}")
        return None
