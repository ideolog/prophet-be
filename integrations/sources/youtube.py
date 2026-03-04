from django.conf import settings
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

class YouTubeIntegration:
    def fetch_content(self, source, source_config):
        video_id = source_config.get("video_id")
        channel_id = source_config.get("channel_id")
        latest = source_config.get("latest", False)
        language = source_config.get("language", "en")

        if latest and channel_id:
            # Use YouTube API to find the latest video
            api_key = getattr(settings, "YOUTUBE_API_KEY", None)
            if not api_key:
                raise ValueError("YOUTUBE_API_KEY not configured")
            
            youtube = build("youtube", "v3", developerKey=api_key)
            
            # Search for the latest video, excluding shorts by filtering for longer videos
            # We use videoDuration='medium' or 'long' to avoid shorts (which are usually < 60s)
            # However, the search().list() videoDuration filter only works with type='video'
            search_response = youtube.search().list(
                channelId=channel_id,
                part="id,snippet",
                order="date",
                maxResults=5, # Get a few recent ones to find the first non-short
                type="video",
                videoDuration="medium" # 'medium' is 4-20 min, 'long' is > 20 min. 
                                       # 'any' includes shorts. 
                                       # Let's try 'any' first and filter manually if we want more precision,
                                       # or use 'medium' and 'long' separately.
            ).execute()

            if not search_response.get("items"):
                # If no medium videos, try long
                search_response = youtube.search().list(
                    channelId=channel_id,
                    part="id,snippet",
                    order="date",
                    maxResults=5,
                    type="video",
                    videoDuration="long"
                ).execute()

            if not search_response.get("items"):
                raise ValueError(f"No long/medium videos found for channel {channel_id}")
            
            # Take the most recent one from the filtered results
            video_id = search_response["items"][0]["id"]["videoId"]
            video_title = search_response["items"][0]["snippet"]["title"]
        else:
            video_title = f"YouTube video {video_id}"

        if not video_id:
            raise ValueError("video_id or channel_id with latest=True is required")

        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=[language])
        
        return {
            "video_id": video_id, 
            "transcript": fetched,
            "title": video_title
        }

    def normalize_to_rawtext(self, raw_data, source=None, source_config=None):
        video_id = raw_data["video_id"]
        video_title = raw_data.get("title", f"YouTube video {video_id}")
        formatter = TextFormatter()
        text = formatter.format_transcript(raw_data["transcript"])

        return [{
            "title": video_title,
            "subtitle": None,
            "author": source.name if source else None,
            "content": text,
            "published_at": None, # Could be fetched from API if needed
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
        }]
