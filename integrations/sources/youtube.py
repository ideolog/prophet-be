import html
from django.conf import settings
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

class YouTubeIntegration:
    def fetch_content(self, source, source_config):
        video_id = source_config.get("video_id")
        channel_id = source_config.get("channel_id") or (source.external_id if source.platform == 'youtube' else None)
        limit = int(source_config.get("limit", 3))
        language = source_config.get("language", "en")

        if not video_id and channel_id:
            # Use YouTube API to find the latest videos
            api_key = getattr(settings, "YOUTUBE_API_KEY", None)
            if not api_key:
                raise ValueError("YOUTUBE_API_KEY not configured")
            
            youtube = build("youtube", "v3", developerKey=api_key)
            
            # Search for the latest videos, excluding shorts
            search_response = youtube.search().list(
                channelId=channel_id,
                part="id,snippet",
                order="date",
                maxResults=limit * 2, # Get more to filter shorts
                type="video",
                videoDuration="medium" 
            ).execute()

            if not search_response.get("items"):
                search_response = youtube.search().list(
                    channelId=channel_id,
                    part="id,snippet",
                    order="date",
                    maxResults=limit * 2,
                    type="video",
                    videoDuration="long"
                ).execute()

            if not search_response.get("items"):
                raise ValueError(f"No long/medium videos found for channel {channel_id}")
            
            # Return list of video data
            videos = []
            for item in search_response.get("items", [])[:limit]:
                v_id = item["id"]["videoId"]
                v_title = html.unescape(item["snippet"]["title"])
                videos.append({"video_id": v_id, "title": v_title})
            return videos
        
        # Single video mode
        if video_id:
            return [{"video_id": video_id, "title": source_config.get("title", f"YouTube video {video_id}")}]

        raise ValueError("video_id or channel_id is required")

    def normalize_to_rawtext(self, raw_data, source=None, source_config=None):
        if not isinstance(raw_data, list):
            raw_data = [raw_data]
            
        results = []
        api = YouTubeTranscriptApi()
        language = source_config.get("language", "en") if source_config else "en"

        for video in raw_data:
            try:
                video_id = video["video_id"]
                video_title = video.get("title", f"YouTube video {video_id}")
                
                fetched = api.fetch(video_id, languages=[language])
                
                # Custom formatting to include timestamps
                # Format: [MM:SS] Text
                formatted_lines = []
                for entry in fetched:
                    # entry is a FetchedTranscriptSnippet object with .text, .start, .duration
                    start_time = int(entry.start)
                    minutes = start_time // 60
                    seconds = start_time % 60
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"
                    text = entry.text.replace('\n', ' ').strip()
                    formatted_lines.append(f"{timestamp} {text}")
                
                full_text = "\n".join(formatted_lines)

                results.append({
                    "title": video_title,
                    "subtitle": None,
                    "author": source.name if source else None,
                    "content": full_text,
                    "published_at": None,
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                })
            except Exception as e:
                print(f"DEBUG: Failed to fetch transcript for {video.get('video_id')}: {e}")
                continue
                
        return results
