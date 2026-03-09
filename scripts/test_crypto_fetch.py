import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
import sys
sys.path.append('.')
django.setup()

from narratives.models import Source
from integrations.core.integration_registry import INTEGRATION_REGISTRY

def test_fetch(slug):
    source = Source.objects.get(slug=slug)
    integration = INTEGRATION_REGISTRY.get(slug)
    
    if not integration:
        print(f"No integration found for {slug}")
        return

    print(f"Fetching content for {source.name}...")
    raw_data = integration.fetch_content(source, {"limit": 2})
    print(f"Fetched {len(raw_data)} articles.")
    
    for i, article in enumerate(raw_data):
        print(f"\n--- Article {i+1} ---")
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        
    print("\nNormalizing to rawtext...")
    normalized = integration.normalize_to_rawtext(raw_data, source, {"limit": 2})
    print(f"Normalized {len(normalized)} articles.")
    
    for i, rt in enumerate(normalized):
        print(f"\n--- Normalized Article {i+1} ---")
        print(f"Title: {rt['title']}")
        print(f"Content Length: {len(rt['content'])}")
        print(f"Content Preview: {rt['content'][:200]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_fetch(sys.argv[1])
    else:
        for slug in ["the-block", "decrypt", "cointelegraph"]:
            test_fetch(slug)
            print("\n" + "="*50 + "\n")
