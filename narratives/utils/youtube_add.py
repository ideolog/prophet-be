# narratives/utils/youtube_add.py
"""Add a YouTube channel by URL. Used by YouTubeSourceAddView and add_crypto_youtube_channels command."""

import re
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from googleapiclient.discovery import build

from narratives.models import Source, Topic


def add_youtube_channel_by_url(url: str, avatar_file=None):
    """
    Resolve URL to channel ID, fetch channel info, create Source if not exists.
    Returns (source, created). Raises ValueError on duplicate or missing channel.
    """
    api_key = getattr(settings, "YOUTUBE_API_KEY", None)
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY not configured in settings")

    url = url.strip().rstrip("/")
    youtube = build("youtube", "v3", developerKey=api_key)

    external_id = None
    handle = None

    if "@" in url:
        handle = "@" + url.split("@")[1].split("/")[0].split("?")[0]
        search_response = youtube.search().list(
            q=handle, type="channel", part="id,snippet", maxResults=1
        ).execute()
        if search_response.get("items"):
            external_id = search_response["items"][0]["id"]["channelId"]
    elif "channel/" in url:
        external_id = url.split("channel/")[1].split("/")[0].split("?")[0]
    elif "user/" in url:
        user_name = url.split("user/")[1].split("/")[0].split("?")[0]
        user_response = youtube.channels().list(forUsername=user_name, part="id").execute()
        if user_response.get("items"):
            external_id = user_response["items"][0]["id"]

    if not external_id:
        search_response = youtube.search().list(
            q=url, type="channel", part="id", maxResults=1
        ).execute()
        if search_response.get("items"):
            external_id = search_response["items"][0]["id"]["channelId"]

    if not external_id:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        external_id_meta = soup.find("meta", itemprop="channelId")
        if external_id_meta:
            external_id = external_id_meta["content"]
        if not external_id:
            match = re.search(r'channelId":"(UC[a-zA-Z0-9_-]+)"', response.text)
            if match:
                external_id = match.group(1)
            else:
                match = re.search(r'browse_id":"(UC[a-zA-Z0-9_-]+)"', response.text)
                if match:
                    external_id = match.group(1)

    if not external_id:
        raise ValueError(f"Could not determine YouTube channel ID for URL: {url}")

    channel_response = youtube.channels().list(
        id=external_id, part="snippet,statistics"
    ).execute()
    if not channel_response.get("items"):
        raise ValueError("Channel not found via YouTube API")

    item = channel_response["items"][0]
    snippet = item["snippet"]
    stats = item["statistics"]
    name = snippet.get("title")
    description = snippet.get("description")
    avatar_url = snippet.get("thumbnails", {}).get("high", {}).get("url")
    subscriber_count = int(stats.get("subscriberCount", 0))
    custom_url = snippet.get("customUrl")
    if custom_url and not handle:
        handle = custom_url if custom_url.startswith("@") else "@" + custom_url

    existing_by_id = Source.objects.filter(external_id=external_id).first()
    if existing_by_id:
        raise ValueError(f"Duplicate channel: '{existing_by_id.name}' already exists with ID {external_id}")

    existing_by_name = Source.objects.filter(name=name).first()
    if existing_by_name:
        raise ValueError(f"Duplicate name: A source with the name '{name}' already exists.")

    source = Source.objects.create(
        external_id=external_id,
        name=name,
        platform="youtube",
        handle=handle,
        description=description,
        avatar_url=avatar_url,
        subscriber_count=subscriber_count,
        url=f"https://www.youtube.com/channel/{external_id}",
    )
    if avatar_file:
        source.avatar_file = avatar_file
        source.save()

    if not source.topic:
        blockchain_topic, _ = Topic.objects.get_or_create(name="Blockchain")
        source.topic = blockchain_topic
        source.save()

    return source, True
