# integrations/sources/youtube.py
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

class YouTubeIntegration:
    def fetch_content(self, source_config):
        video_id = source_config["video_id"]
        # если хочешь язык: source_config.get("languages", ["en"])
        transcript = YouTubeTranscriptApi.get_transcript(video_id)  # или fetch(...) как в доке
        return {"video_id": video_id, "transcript": transcript}

    def normalize_to_rawtext(self, raw_data, source_config):
        video_id = raw_data["video_id"]
        formatter = TextFormatter()
        text = formatter.format_transcript(raw_data["transcript"])

        return [{
            "title": f"YouTube video {video_id}",
            "subtitle": None,
            "author": None,
            "content": text,
            "published_at": None,
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
        }]
