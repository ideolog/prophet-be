import os
import django
import requests
from bs4 import BeautifulSoup

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prophet_be.settings')
import sys
sys.path.append('.')
django.setup()

from django.conf import settings
from googleapiclient.discovery import build
from narratives.models import Source, Topic

def add_youtube_channels():
    api_key = getattr(settings, "YOUTUBE_API_KEY", None)
    if not api_key:
        print("Error: YOUTUBE_API_KEY not configured in settings")
        return

    youtube = build("youtube", "v3", developerKey=api_key)
    blockchain_topic, _ = Topic.objects.get_or_create(name="Blockchain")

    # List of high-quality blockchain/crypto YouTube channels
    channel_urls = [
        "https://www.youtube.com/@CoinBureau",
        "https://www.youtube.com/@Bankless",
        "https://www.youtube.com/@WhiteboardCrypto",
        "https://www.youtube.com/@BenjaminCowen",
        "https://www.youtube.com/@AltcoinDaily",
        "https://www.youtube.com/@TheMoon",
        "https://www.youtube.com/@CryptoLark",
        "https://www.youtube.com/@EllioTradesCrypto",
        "https://www.youtube.com/@DataDash",
        "https://www.youtube.com/@AndreasAntonopoulos",
        "https://www.youtube.com/@Boxmining"
    ]

    for url in channel_urls:
        try:
            print(f"Processing {url}...")
            # 1. Extract handle or channel ID from URL
            external_id = None
            handle = None
            
            if "@" in url:
                handle = "@" + url.split("@")[1].split("/")[0].split("?")[0]
                # Search channel by handle
                search_response = youtube.search().list(
                    q=handle,
                    type="channel",
                    part="id",
                    maxResults=1
                ).execute()
                
                if search_response.get("items"):
                    external_id = search_response["items"][0]["id"]["channelId"]
            
            if not external_id:
                # Fallback to scraping
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                external_id_meta = soup.find("meta", itemprop="channelId")
                external_id = external_id_meta["content"] if external_id_meta else None

            if not external_id:
                print(f"Could not determine channel ID for {url}")
                continue

            # 2. Get full channel details via API
            channel_response = youtube.channels().list(
                id=external_id,
                part="snippet,statistics"
            ).execute()

            if not channel_response.get("items"):
                print(f"Channel {external_id} not found via YouTube API")
                continue

            item = channel_response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]

            name = snippet.get("title")
            description = snippet.get("description")
            avatar_url = snippet.get("thumbnails", {}).get("high", {}).get("url")
            subscriber_count = int(stats.get("subscriberCount", 0))

            # 3. Create or update the source
            source, created = Source.objects.update_or_create(
                external_id=external_id,
                defaults={
                    "name": name,
                    "platform": "youtube",
                    "handle": handle,
                    "description": description,
                    "avatar_url": avatar_url,
                    "subscriber_count": subscriber_count,
                    "url": f"https://www.youtube.com/channel/{external_id}",
                    "topic": blockchain_topic,
                    "is_new": False
                }
            )

            if created:
                print(f"Created YouTube source: {name}")
            else:
                print(f"Updated YouTube source: {name}")

        except Exception as e:
            print(f"Error processing {url}: {e}")

if __name__ == "__main__":
    add_youtube_channels()
