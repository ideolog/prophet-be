import re
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.shortcuts import get_object_or_404
from googleapiclient.discovery import build
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from ..models import RawText, Source, Topic, PendingTopic, RawTextProcessing
from ..serializers import RawTextSerializer, SourceSerializer, TopicSerializer, PendingTopicSerializer
from ..utils.text import generate_fingerprint
from ..serializers.request_bodies import RawTextDuplicateCheckRequestSerializer
from narratives.models import Source, RawText, RawTextProcessing, PendingTopic
from narratives.utils.ai_module import suggest_topics_for_text

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

class RawTextFindTopicsView(APIView):
    def post(self, request, id):
        rawtext = get_object_or_404(RawText, id=id)
        reset = request.data.get("reset", False)
        
        if reset:
            # Delete all existing pending topics for this rawtext
            PendingTopic.objects.filter(rawtext=rawtext).delete()
        
        from ..models.categories import AppConfiguration
        from django.utils import timezone
        
        current_version = AppConfiguration.get_version("categorization_version")
        
        # Get all topics with their keywords, excluding placeholders
        topics = Topic.objects.filter(is_placeholder=False)
        topics_data = [
            {
                "id": t.id, 
                "name": t.name, 
                "alternative_name": t.alternative_name,
                "keywords": t.keywords,
                "weak_keywords": t.weak_keywords
            }
            for t in topics
        ]
        
        # Call search module to suggest topics
        suggestions = suggest_topics_for_text(rawtext.content, topics_data)
        
        created_count = 0
        for sug in suggestions:
            topic_id = sug.get("topic_id")
            context = sug.get("context")
            matched_keyword = sug.get("matched_keyword")
            is_weak = sug.get("is_weak", False)
            
            if topic_id and context:
                try:
                    topic = Topic.objects.get(id=topic_id)
                    # We still want to avoid exact duplicates (same topic, same context)
                    if not PendingTopic.objects.filter(rawtext=rawtext, topic=topic, context=context).exists():
                        PendingTopic.objects.create(
                            rawtext=rawtext,
                            topic=topic,
                            context=context,
                            status="pending",
                            matched_keyword=matched_keyword,
                            is_weak=is_weak,
                            found_context_words=sug.get("found_context_words", [])
                        )
                        created_count += 1
                except Topic.DoesNotExist:
                    continue
        
        # Update categorization metadata
        rawtext.categorization_version = current_version
        rawtext.last_categorized_at = timezone.now()
        rawtext.save()
        
        return Response({
            "message": f"Found {len(suggestions)} suggestions, created {created_count} new pending topics.",
            "suggestions_count": len(suggestions)
        }, status=status.HTTP_200_OK)

class PendingTopicActionView(APIView):
    def post(self, request, id):
        pending = get_object_or_404(PendingTopic, id=id)
        action = request.data.get("action") # 'approve', 'decline', 'approve_all', 'remove_keyword'
        
        if action == 'approve':
            pending.status = 'approved'
            pending.save()
            return Response({"message": "Topic approved"}, status=status.HTTP_200_OK)
        elif action == 'approve_all':
            # Approve all pending occurrences of the same topic for the same rawtext
            count = PendingTopic.objects.filter(
                rawtext=pending.rawtext,
                topic=pending.topic,
                status='pending'
            ).update(status='approved')
            return Response({"message": f"Approved {count} occurrences of '{pending.topic.name}'"}, status=status.HTTP_200_OK)
        elif action == 'decline':
            pending.status = 'declined'
            pending.save()
            return Response({"message": "Topic declined"}, status=status.HTTP_200_OK)
        elif action == 'remove_keyword':
            keyword = pending.matched_keyword
            if not keyword:
                return Response({"error": "No keyword associated with this suggestion"}, status=status.HTTP_400_BAD_REQUEST)
            
            topic = pending.topic
            if keyword == topic.name:
                return Response({"error": "Cannot remove the topic name itself as a keyword"}, status=status.HTTP_400_BAD_REQUEST)
            
            if keyword in topic.keywords:
                # 1. Remove keyword from topic's global rules
                topic.keywords = [kw for kw in topic.keywords if kw != keyword]
                topic.save()
                
                # 2. Mark ALL pending occurrences of this keyword for this topic as 'declined' 
                # across ALL articles (because the rule is gone globally)
                count = PendingTopic.objects.filter(
                    topic=topic,
                    matched_keyword=keyword,
                    status='pending'
                ).update(status='declined')
                
                return Response({
                    "message": f"Keyword '{keyword}' removed from topic '{topic.name}'. {count} pending suggestions declined."
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": f"Keyword '{keyword}' not found in topic keywords"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

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

class TopicListView(generics.ListAPIView):
    queryset = Topic.objects.all().order_by('name')
    serializer_class = TopicSerializer

    def get_queryset(self):
        queryset = Topic.objects.all().order_by('name')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class TopicCreateView(generics.CreateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

    def perform_create(self, serializer):
        parents_ids = self.request.data.get('parents_ids', [])
        related_ids = self.request.data.get('related_ids', [])
        instance = serializer.save()
        if parents_ids:
            instance.parents.set(parents_ids)
        if related_ids:
            instance.related_topics.set(related_ids)

class TopicDetailView(generics.RetrieveUpdateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle parents_ids, related_ids, and school_ids if provided
        parents_ids = request.data.get('parents_ids')
        related_ids = request.data.get('related_ids')
        school_ids = request.data.get('school_ids')
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        if parents_ids is not None:
            instance.parents.set(parents_ids)
        if related_ids is not None:
            instance.related_topics.set(related_ids)
        if school_ids is not None:
            instance.schools_of_thought.set(school_ids)
            
        return Response(serializer.data)

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
        return Response({"error": "Mass processing is temporarily disabled."}, status=status.HTTP_400_BAD_REQUEST)
