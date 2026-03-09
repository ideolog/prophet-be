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

from ..models import RawText, Source, Topic, PendingTopic, TopicType
from ..serializers import RawTextSerializer, SourceSerializer, TopicSerializer, TopicTypeSerializer, PendingTopicSerializer, DeclinedTopicSerializer
from ..utils.text import generate_fingerprint
from ..serializers.request_bodies import RawTextDuplicateCheckRequestSerializer
from narratives.models import Source, RawText, PendingTopic, TopicType
from narratives.models.categories import DeclinedTopic, Topic, TopicType
from narratives.utils.ai_module import suggest_topics_for_text
from narratives.utils.knowledge_sources.aggregator import collect_topic_knowledge, format_knowledge_dossier
from narratives.utils.local_ai import analyze_topic_with_ai
import wikipediaapi
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

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
            if keyword.lower() == topic.name.lower():
                return Response({"error": "Cannot remove the topic name itself as a keyword"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 1. Remove keyword from topic's global rules (check both strong and weak)
            keyword_removed = False
            
            # Check strong keywords
            if keyword in topic.keywords:
                topic.keywords = [kw for kw in topic.keywords if kw != keyword]
                keyword_removed = True
            
            # Check weak keywords
            if not keyword_removed:
                new_weak = [w for w in topic.weak_keywords if w.get('keyword') != keyword]
                if len(new_weak) < len(topic.weak_keywords):
                    topic.weak_keywords = new_weak
                    keyword_removed = True
            
            if keyword_removed:
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
    queryset = Topic.objects.all().order_by('-updated_at')
    serializer_class = TopicSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Topic.objects.all().order_by('-updated_at')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class TopicTypeListView(generics.ListCreateAPIView):
    queryset = TopicType.objects.all().order_by('name')
    serializer_class = TopicTypeSerializer

class TopicTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TopicType.objects.all()
    serializer_class = TopicTypeSerializer
    lookup_field = "id"

class TopicTypeListView(generics.ListCreateAPIView):
    queryset = TopicType.objects.all().order_by('name')
    serializer_class = TopicTypeSerializer

class TopicTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TopicType.objects.all()
    serializer_class = TopicTypeSerializer
    lookup_field = "id"

class DeclinedTopicListView(generics.ListAPIView):
    queryset = DeclinedTopic.objects.all().order_by('-created_at')
    serializer_class = DeclinedTopicSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = DeclinedTopic.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class TopicCreateView(generics.CreateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

    def perform_create(self, serializer):
        related_ids = self.request.data.get('related_ids', [])
        instance = serializer.save()
        if related_ids:
            instance.related_topics.set(related_ids)

class TopicDetailView(generics.RetrieveUpdateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle related_ids and school_ids if provided
        related_ids = request.data.get('related_ids')
        school_ids = request.data.get('school_ids')
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        if related_ids is not None:
            instance.related_topics.set(related_ids)
        if school_ids is not None:
            instance.schools_of_thought.set(school_ids)
            
        return Response(serializer.data)

class TopicBulkDeleteView(APIView):
    def post(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        count = Topic.objects.filter(id__in=ids).count()
        Topic.objects.filter(id__in=ids).delete()
        
        return Response({"message": f"Successfully deleted {count} topics."}, status=status.HTTP_200_OK)

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

class RawTextAISuggestTopicsView(APIView):
    def post(self, request, id):
        rawtext = get_object_or_404(RawText, id=id)
        
        # 1. Get existing topics already linked to this text
        existing_linked_topic_ids = PendingTopic.objects.filter(rawtext=rawtext).values_list('topic_id', flat=True)
        existing_topics_map = {t.name.lower(): t for t in Topic.objects.filter(id__in=existing_linked_topic_ids)}
        existing_topic_names = [t.name for t in existing_topics_map.values()]
        
        # 2. Hybrid Extraction: spaCy NER + Local AI
        
        # 2a. spaCy NER (PERSON, ORG)
        from narratives.utils.ai_module import extract_entities_with_spacy
        spacy_entities = extract_entities_with_spacy(rawtext.content)
        
        # 2b. Local AI (Abstract concepts)
        from narratives.utils.local_ai import suggest_new_topics_with_ai
        ai_results = suggest_new_topics_with_ai(rawtext.content[:4000], existing_topic_names)
        
        if not ai_results or "suggested_topics" not in ai_results:
            return Response({"error": "AI failed to suggest topics."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        ai_suggestions = ai_results["suggested_topics"]
        
        # 3. Merge and Filter suggestions
        # We'll use a dict keyed by lowercase name to deduplicate
        merged_suggestions = {} # name_lower -> {name, type_id, type_name, is_ner}
        
        # Add NER entities first (higher confidence for specific names)
        for ent in spacy_entities:
            name_lower = ent["name"].lower()
            merged_suggestions[name_lower] = {
                "name": ent["name"],
                "suggested_type_id": ent["suggested_type_id"],
                "suggested_type_name": ent["suggested_type_name"],
                "is_ner": True
            }
        
        # Add AI suggestions
        for name in ai_suggestions:
            name_lower = name.lower().strip()
            if name_lower and name_lower not in merged_suggestions:
                merged_suggestions[name_lower] = {
                    "name": name.strip(),
                    "suggested_type_id": None,
                    "suggested_type_name": None,
                    "is_ner": False
                }
        
        valid_suggestions = []
        rejected_suggestions = []
        
        from narratives.utils.ai_module import _get_nlp
        nlp = _get_nlp()
        user_agent = "ProphetOntologyBot/1.0 (https://github.com/paulus/prophet; contact@example.com)"
        wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language='en')

        for name_lower, info in merged_suggestions.items():
            name = info["name"]
            if len(name) < 2: continue
            
            # Check if already linked to THIS article
            is_already_linked = name_lower in existing_topics_map
            
            # Check if already exists in DB (case-insensitive)
            topic_obj = Topic.objects.filter(name__iexact=name).first()
            
            # POS Check (Only for AI suggestions, NER is already high confidence proper nouns)
            if not info["is_ner"] and not topic_obj:
                doc = nlp(name)
                if len(doc) > 0 and doc[0].pos_ in ["VERB", "AUX"]:
                    rejected_suggestions.append({"name": name, "reason": "Starts with verb"})
                    continue
                
            # Wikipedia Check (Only if not in DB)
            summary = ""
            if not topic_obj:
                page = wiki.page(name)
                if not page.exists():
                    rejected_suggestions.append({"name": name, "reason": "Wikipedia page missing"})
                    continue
                name = page.title # Use canonical Wikipedia title
                summary = page.summary[:200] + "..."
            else:
                summary = (topic_obj.description or "")[:200] + "..."

            valid_suggestions.append({
                "name": name,
                "exists_in_db": topic_obj is not None,
                "topic_id": topic_obj.id if topic_obj else None,
                "is_already_linked": is_already_linked,
                "suggested_type_id": info["suggested_type_id"],
                "suggested_type_name": info["suggested_type_name"],
                "summary": summary
            })
            
        # 4. Save to cache
        rawtext.ai_suggestions = valid_suggestions
        rawtext.save()
            
        return Response({
            "suggestions": valid_suggestions,
            "rejected": rejected_suggestions
        }, status=status.HTTP_200_OK)

class TopicDistributionView(APIView):
    def get(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        
        # 1. Get all approved mentions of this topic
        pending_topics = PendingTopic.objects.filter(
            topic=topic,
            status="approved",
        ).select_related('rawtext', 'topic')

        if not pending_topics.exists():
            return Response({
                "id": topic.id,
                "name": topic.name,
                "total_weight": 0,
                "breakdown": []
            })

        # 2. Calculate weights
        total_weight = 0
        # Track if we've already given the title weight for a topic in a specific article
        title_weight_given = set() # (rawtext_id, topic_id)

        for pt in pending_topics:
            rawtext_id = pt.rawtext_id
            
            weight = 1
            if (rawtext_id, topic.id) not in title_weight_given:
                title = (pt.rawtext.title or "").lower()
                matched = (pt.matched_keyword or topic.name).lower()
                if matched and title.find(matched) != -1:
                    weight = 10
                    title_weight_given.add((rawtext_id, topic.id))
            
            total_weight += weight

        return Response({
            "id": topic.id,
            "name": topic.name,
            "total_weight": total_weight,
            "breakdown": [
                {
                    "id": None,
                    "name": "Direct Mentions",
                    "weight": total_weight
                }
            ]
        })

class TopicEnhanceWikipediaView(APIView):
    def post(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        
        # 1. Collect knowledge from multiple sources
        knowledge_list = collect_topic_knowledge(topic.name, wikipedia_url=topic.wikipedia_url)
        if not knowledge_list:
            return Response({"error": f"No information found for '{topic.name}' in any source."}, status=status.HTTP_404_NOT_FOUND)
        
        # 2. Update Topic Description if empty or different (prefer Binance Academy for crypto)
        best_content = knowledge_list[0]['content']
        if not topic.description or len(topic.description) < 50:
            topic.description = best_content
            topic.save()
            
        # 3. Analyze with Local AI using the combined dossier
        dossier = format_knowledge_dossier(knowledge_list)
        ai_results = analyze_topic_with_ai(topic.name, dossier)
        
        if not ai_results:
            return Response({
                "message": "Knowledge collected, but AI analysis failed (check Ollama).",
                "dossier": dossier
            }, status=status.HTTP_200_OK)
            
        # 4. Apply findings (Create missing topics and link them)
        created_topics = []
        linked_schools = []
        linked_related = []
        rejected_count = 0
        
        # Helper to get or create topic with validation
        def get_or_create_topic(name, target_field):
            nonlocal rejected_count
            name = name.strip()
            if not name: return None
            
            # 0. Case-insensitive existence check to avoid duplicates
            existing = Topic.objects.filter(name__iexact=name).first()
            if existing:
                return existing

            # 1. Basic length check
            if len(name) < 2:
                DeclinedTopic.objects.create(
                    name=name,
                    source_topic=topic,
                    target_field=target_field,
                    reason='too_short'
                )
                rejected_count += 1
                return None

            # 2. POS Validation with spaCy (Anti-verb check)
            try:
                from narratives.utils.ai_module import _get_nlp
                nlp = _get_nlp()
                doc = nlp(name)
                if len(doc) > 0:
                    first_token = doc[0]
                    # Check if first token is a verb OR if it's a participle (like 'Written')
                    # spaCy tags: VERB (main verb), AUX (auxiliary), PART (particle)
                    if first_token.pos_ in ["VERB", "AUX"]:
                        DeclinedTopic.objects.create(
                            name=name,
                            source_topic=topic,
                            target_field=target_field,
                            reason='starts_with_verb',
                            reason_detail=f"Detected POS: {first_token.pos_} ({first_token.tag_})"
                        )
                        rejected_count += 1
                        return None
            except Exception as e:
                print(f"POS validation failed: {e}")

            # 3. Wikipedia Existence Check (Final sanity check for new topics)
            try:
                user_agent = "ProphetOntologyBot/1.0 (https://github.com/paulus/prophet; contact@example.com)"
                wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language='en')
                page = wiki.page(name)
                if not page.exists():
                    # Also check if it exists in our DB already
                    if not Topic.objects.filter(name__iexact=name).exists():
                        DeclinedTopic.objects.create(
                            name=name,
                            source_topic=topic,
                            target_field=target_field,
                            reason='wikipedia_missing',
                            reason_detail="No exact match found on English Wikipedia"
                        )
                        rejected_count += 1
                        return None
            except Exception as e:
                print(f"Wikipedia check failed: {e}")

            # 4. Create or get
            name = name[0].upper() + name[1:] if len(name) > 0 else name
            t, created = Topic.objects.get_or_create(name=name)
            if created:
                created_topics.append(name)
            return t

        # Process Schools of Thought
        for s_name in ai_results.get("schools", []):
            s_topic = get_or_create_topic(s_name, "schools")
            if s_topic and s_topic != topic:
                topic.schools_of_thought.add(s_topic)
                linked_schools.append(s_name)

        # Process Related Topics from AI results
        for r_name in ai_results.get("related", []):
            r_topic = get_or_create_topic(r_name, "related")
            if r_topic and r_topic != topic:
                topic.related_topics.add(r_topic)
                linked_related.append(r_name)
        
        # Process discovery links from Wikipedia (Summary/Overview)
        discovery_links = []
        for knowledge in knowledge_list:
            if knowledge.get('source') == 'Wikipedia' and 'related_links' in knowledge:
                discovery_links = knowledge['related_links']
                break
        
        discovered_topics_count = 0
        for link in discovery_links:
            link_title = link['title']
            link_url = link['url']
            
            # Check if exists or create
            # We use a simplified version of get_or_create_topic logic here
            # but we prioritize Wikipedia URL and canonical title.
            
            # 1. Check by Wikipedia URL first
            r_topic = Topic.objects.filter(wikipedia_url=link_url).first()
            
            # 2. Check by canonical name
            if not r_topic:
                r_topic = Topic.objects.filter(name__iexact=link_title).first()
            
            if not r_topic:
                # Create new topic if it doesn't exist
                # We still want to run basic validation (no verbs, etc.)
                r_topic = get_or_create_topic(link_title, "wikipedia_discovery")
                if r_topic:
                    r_topic.wikipedia_url = link_url
                    r_topic.save()
                    discovered_topics_count += 1
            
            # Link as related if not already linked and not the same topic
            if r_topic and r_topic != topic:
                topic.related_topics.add(r_topic)
                if link_title not in linked_related:
                    linked_related.append(link_title)
                
        return Response({
            "message": "Topic enhanced successfully.",
            "sources_used": [s['source'] for s in knowledge_list],
            "ai_extracted": ai_results,
            "created_new_topics": created_topics,
            "linked_schools": linked_schools,
            "linked_related": linked_related,
            "discovered_from_wikipedia": discovered_topics_count,
            "rejected_suggestions_count": rejected_count,
            "summary": best_content
        }, status=status.HTTP_200_OK)

class TopicMergeView(APIView):
    def post(self, request):
        source_id = request.data.get("source_id")
        target_id = request.data.get("target_id")
        new_name = request.data.get("name")
        new_alt_name = request.data.get("alternative_name")
        new_type_id = request.data.get("topic_type_id")
        new_school_ids = request.data.get("school_ids", [])

        if not source_id or not target_id:
            return Response({"error": "Source and target IDs are required"}, status=status.HTTP_400_BAD_REQUEST)

        source = get_object_or_404(Topic, id=source_id)
        target = get_object_or_404(Topic, id=target_id)

        # 1. Update target with new basic info
        if new_name:
            target.name = new_name
        if new_alt_name is not None:
            target.alternative_name = new_alt_name
        
        if new_type_id:
            target.topic_type_id = new_type_id
        
        if new_school_ids:
            target.schools_of_thought.set(new_school_ids)

        # 2. Merge Keywords
        strong_kws = set(target.keywords)
        strong_kws.update(source.keywords)
        target.keywords = list(strong_kws)

        # Merge weak keywords (avoid duplicates by keyword string)
        weak_kws_map = {w['keyword']: w for w in target.weak_keywords}
        for w in source.weak_keywords:
            if w['keyword'] not in weak_kws_map:
                weak_kws_map[w['keyword']] = w
        target.weak_keywords = list(weak_kws_map.values())

        # 3. Merge Relations
        # Related topics
        target.related_topics.add(*source.related_topics.all())
        # Remove self from related if it was there
        target.related_topics.remove(target)
        
        # 4. Re-link PendingTopics
        # Move all mentions from source to target
        PendingTopic.objects.filter(topic=source).update(topic=target)

        # 5. Handle metadata merge (simple dict update)
        if source.metadata:
            merged_metadata = target.metadata or {}
            merged_metadata.update(source.metadata)
            target.metadata = merged_metadata

        # 6. Final save and delete source
        target.save()
        source.delete()

        return Response({
            "message": f"Successfully merged topic {source_id} into {target_id}",
            "target_id": target.id
        }, status=status.HTTP_200_OK)
