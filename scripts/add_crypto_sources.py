import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
django.setup()

from narratives.models import Source, Topic

def add_sources():
    # Ensure "Blockchain" topic exists
    blockchain_topic, _ = Topic.objects.get_or_create(name="Blockchain")

    sources_to_add = [
        {
            "name": "The Block",
            "slug": "the-block",
            "url": "https://www.theblock.co/",
            "rss_url": "https://www.theblock.co/rss.xml",
            "platform": "direct",
            "description": "The Block is the leading information services brand in the digital asset space.",
            "avatar_url": "https://unavatar.io/theblock.co",
            "topic": blockchain_topic
        },
        {
            "name": "Decrypt",
            "slug": "decrypt",
            "url": "https://decrypt.co/",
            "rss_url": "https://decrypt.co/feed",
            "platform": "direct",
            "description": "Decrypt is a next-generation media company and creative studio at the intersection of technology and culture.",
            "avatar_url": "https://unavatar.io/decrypt.co",
            "topic": blockchain_topic
        },
        {
            "name": "CoinTelegraph",
            "slug": "cointelegraph",
            "url": "https://cointelegraph.com/",
            "rss_url": "https://cointelegraph.com/rss",
            "platform": "direct",
            "description": "Cointelegraph is the leading independent digital media resource covering a wide range of news on blockchain technology, crypto assets, and emerging fintech trends.",
            "avatar_url": "https://unavatar.io/cointelegraph.com",
            "topic": blockchain_topic
        }
    ]

    for s_data in sources_to_add:
        source, created = Source.objects.update_or_create(
            slug=s_data["slug"],
            defaults={
                "name": s_data["name"],
                "url": s_data["url"],
                "rss_url": s_data["rss_url"],
                "platform": s_data["platform"],
                "description": s_data["description"],
                "avatar_url": s_data["avatar_url"],
                "topic": s_data["topic"],
                "is_new": False
            }
        )
        if created:
            print(f"Created source: {source.name}")
        else:
            print(f"Updated source: {source.name}")

if __name__ == "__main__":
    add_sources()
