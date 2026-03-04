import re
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from googleapiclient.discovery import build
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from ..models import RawText, Source
from ..serializers import RawTextSerializer, SourceSerializer
from ..utils.text import generate_fingerprint
from ..serializers.request_bodies import RawTextDuplicateCheckRequestSerializer
from narratives.models import Claim, VerificationStatus
from narratives.models.sources import RawText, RawTextProcessing, Source
from narratives.utils.ai_module import extract_narrative_claims  # You must define this helper

class SourceListView(generics.ListCreateAPIView):
    queryset = Source.objects.all().order_by('-created_at')
    serializer_class = SourceSerializer

class SourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    lookup_field = "id"

class YouTubeSourceAddView(APIView):
    def post(self, request):
        url = request.data.get("url")
        avatar_file = request.FILES.get("avatar_file")
        
        if not url:
            return Response({"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = getattr(settings, "YOUTUBE_API_KEY", None)
        if not api_key:
            return Response({"error": "YOUTUBE_API_KEY not configured in settings"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            youtube = build("youtube", "v3", developerKey=api_key)
            
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
            elif "channel/" in url:
                external_id = url.split("channel/")[1].split("/")[0].split("?")[0]
            
            if not external_id:
                # Fallback to scraping if API search failed or URL is different
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                external_id_meta = soup.find("meta", itemprop="channelId")
                external_id = external_id_meta["content"] if external_id_meta else None
                
                if not external_id:
                    match = re.search(r'channelId":"(UC[a-zA-Z0-9_-]+)"', response.text)
                    if match: external_id = match.group(1)

            if not external_id:
                return Response({"error": "Could not determine YouTube channel ID"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Get full channel details via API
            channel_response = youtube.channels().list(
                id=external_id,
                part="snippet,statistics"
            ).execute()

            if not channel_response.get("items"):
                return Response({"error": "Channel not found via YouTube API"}, status=status.HTTP_404_NOT_FOUND)

            item = channel_response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]

            name = snippet.get("title")
            description = snippet.get("description")
            
            # Use YouTube avatar as fallback if no file uploaded
            avatar_url = snippet.get("thumbnails", {}).get("high", {}).get("url")

            subscriber_count = int(stats.get("subscriberCount", 0))
            custom_url = snippet.get("customUrl")
            if custom_url and not handle:
                handle = custom_url if custom_url.startswith("@") else "@" + custom_url

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
                }
            )

            # 4. If avatar file uploaded, save it
            if avatar_file:
                source.avatar_file = avatar_file
                source.save()

            if not source.topic:
                from narratives.models import Topic
                blockchain_topic, _ = Topic.objects.get_or_create(name="Blockchain")
                source.topic = blockchain_topic
                source.save()

            return Response(SourceSerializer(source).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RawTextListView(generics.ListAPIView):
    queryset = RawText.objects.all().order_by('-id')
    serializer_class = RawTextSerializer

class RawTextListCreateView(generics.ListCreateAPIView):
    queryset = RawText.objects.all().order_by("-id")
    serializer_class = RawTextSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data.get("content")
        fingerprint = generate_fingerprint(content)

        existing = RawText.objects.filter(content_fingerprint=fingerprint).first()
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        rawtext = serializer.save(content_fingerprint=fingerprint)
        return Response(self.get_serializer(rawtext).data, status=status.HTTP_201_CREATED)

class RawTextDetailView(generics.RetrieveAPIView):
    queryset = RawText.objects.all()
    serializer_class = RawTextSerializer
    lookup_field = "id"

class RawTextRedownloadView(APIView):
    def post(self, request, id):
        rawtext = get_object_or_404(RawText, id=id)
        
        if rawtext.source.platform != 'youtube':
            return Response({"error": "Redownload only supported for YouTube content"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Extract video ID from source_url (e.g., https://www.youtube.com/watch?v=VIDEO_ID)
        video_id = None
        if rawtext.source_url:
            if 'v=' in rawtext.source_url:
                video_id = rawtext.source_url.split('v=')[1].split('&')[0]
            elif 'be/' in rawtext.source_url:
                video_id = rawtext.source_url.split('be/')[1].split('?')[0]
        
        if not video_id:
            return Response({"error": "Could not determine YouTube video ID from source URL"}, status=status.HTTP_400_BAD_REQUEST)
            
        from integrations.sources.youtube import YouTubeIntegration
        integration = YouTubeIntegration()
        
        try:
            source_config = {"video_id": video_id, "language": "en"}
            raw_data = integration.fetch_content(source=rawtext.source, source_config=source_config)
            normalized = integration.normalize_to_rawtext(raw_data, source=rawtext.source, source_config=source_config)
            
            if not normalized or not normalized[0].get('content'):
                return Response({"error": "Failed to fetch content from YouTube"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            new_content = normalized[0]['content']
            
            # Update the rawtext
            rawtext.content = new_content
            # Update fingerprint if necessary (it will be updated in save() anyway)
            rawtext.is_updated = True
            rawtext.save()
            
            return Response({"message": "Content redownloaded successfully", "content_length": len(new_content)}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": f"Failed to redownload: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RawTextHashDuplicateCheck(APIView):

    @swagger_auto_schema(
        request_body=RawTextDuplicateCheckRequestSerializer,
        responses={200: "Duplicate check result"}
    )
    def post(self, request):
        content = request.data.get("content", "")
        if not content:
            return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

        fingerprint = generate_fingerprint(content)
        duplicate_exists = RawText.objects.filter(content_fingerprint=fingerprint).exists()

        return Response({"duplicate": duplicate_exists}, status=status.HTTP_200_OK)


class RawTextMassProcessingView(APIView):
    def post(self, request):
        default_model = "gpt-4o"

        unprocessed = RawText.objects.exclude(
            processing_records__model_used=default_model
        )

        processed_claim_ids = []

        for raw in unprocessed:
            try:
                extracted_claims = extract_claims_from_text(raw.content)

                for text in extracted_claims:
                    claim = Claim.objects.create(
                        text=text,
                        verification_status=VerificationStatus.objects.get(name="AI Verified"),
                        author=default_model
                    )
                    processed_claim_ids.append(claim.id)

                RawTextProcessing.objects.create(
                    rawtext=raw,
                    model_used=default_model,
                    status="SUCCESS"
                )

            except Exception as e:
                RawTextProcessing.objects.create(
                    rawtext=raw,
                    model_used=default_model,
                    status="FAILED",
                    notes=str(e)
                )

        return Response({
            "processed_rawtexts": unprocessed.count(),
            "created_claims": processed_claim_ids
        }, status=status.HTTP_200_OK)
