import re
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from ..models import RawText, Source, Topic, PendingTopic, TopicType, Epoch
from ..serializers import (
    RawTextSerializer,
    SourceSerializer,
    TopicSerializer,
    TopicTypeSerializer,
    PendingTopicSerializer,
    DeclinedTopicSerializer,
    EpochSerializer,
    AnalyticalFrameworkSerializer,
    AnalyticalCategorySerializer,
)
from ..utils.text import generate_fingerprint, title_contains_keyword_as_word, topic_title_matches_keyword
from ..utils.youtube_add import add_youtube_channel_by_url
from ..serializers.request_bodies import RawTextDuplicateCheckRequestSerializer
from narratives.models import (
    AnalyticalCategory,
    AnalyticalFramework,
    Source,
    RawText,
    PendingTopic,
    TopicType,
    TopicAnalyticalCategory,
)
from narratives.models.categories import DeclinedTopic, Topic, TopicType
from narratives.utils.categorize import run_find_topics_for_rawtext
from narratives.utils.knowledge_sources.aggregator import collect_topic_knowledge, format_knowledge_dossier
from narratives.utils.local_ai import analyze_topic_with_ai, analyze_swot_trigger
import wikipediaapi
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class RawTextStandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
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

        try:
            source, _ = add_youtube_channel_by_url(url, avatar_file=avatar_file)
            return Response(SourceSerializer(source).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            msg = str(e)
            if "YOUTUBE_API_KEY" in msg:
                return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            print(f"DEBUG: YouTubeSourceAddView error: {str(e)}")
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RawTextListView(generics.ListAPIView):
    queryset = RawText.objects.all().order_by("-id")
    serializer_class = RawTextSerializer
    pagination_class = RawTextStandardPagination

    def get_queryset(self):
        queryset = RawText.objects.all().order_by("-id")
        source_id = self.request.query_params.get("source")
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset

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
        suggestions_count, created_count = run_find_topics_for_rawtext(rawtext, reset=reset)
        return Response({
            "message": f"Found {suggestions_count} suggestions, created {created_count} topics (auto-approved).",
            "suggestions_count": suggestions_count,
        }, status=status.HTTP_200_OK)


class RawTextCategorizeAllView(APIView):
    """Run Find Topics on all RawTexts (not yet Done, or all if ?all=1)."""

    def post(self, request):
        from narratives.models.categories import AppConfiguration

        run_all = request.data.get("all", False) if request.data else False
        current_version = AppConfiguration.get_version("categorization_version")

        if run_all:
            qs = RawText.objects.all().order_by("id")
        else:
            qs = RawText.objects.filter(
                Q(categorization_version__isnull=True)
                | ~Q(categorization_version=current_version)
            ).order_by("id")

        total = qs.count()
        if total == 0:
            return Response({
                "processed": 0,
                "created": 0,
                "message": "No RawTexts to process. All are already categorized. Send { \"all\": true } to run on every RawText.",
            }, status=status.HTTP_200_OK)

        created_total = 0
        for rawtext in qs:
            try:
                _, created = run_find_topics_for_rawtext(rawtext, reset=False)
                created_total += created
            except Exception:
                pass

        return Response({
            "processed": total,
            "created": created_total,
            "message": f"Processed {total} RawTexts, created {created_total} PendingTopics.",
        }, status=status.HTTP_200_OK)


class PendingTopicActionView(APIView):
    def post(self, request, id):
        pending = get_object_or_404(PendingTopic, id=id)
        action = request.data.get("action")  # 'approve', 'unapprove', 'decline', 'approve_all', 'remove_keyword'

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
        elif action == 'unapprove':
            if pending.status != 'approved':
                return Response({"error": "Only approved topics can be unapproved"}, status=status.HTTP_400_BAD_REQUEST)
            pending.status = 'pending'
            pending.save()
            return Response({"message": "Topic unapproved (moved to pending)"}, status=status.HTTP_200_OK)
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
            
            # Check strong keywords (entry can be string or dict with 'keyword')
            def strong_kw_matches(entry):
                k = entry if isinstance(entry, str) else entry.get('keyword')
                return k == keyword if k else False
            if any(strong_kw_matches(kw) for kw in topic.keywords):
                topic.keywords = [kw for kw in topic.keywords if not strong_kw_matches(kw)]
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
            
            # Use the first video from the returned list
            if not raw_data or not isinstance(raw_data, list):
                return Response({"error": "No video data found for this ID"}, status=status.HTTP_404_NOT_FOUND)
                
            normalized = integration.normalize_to_rawtext(raw_data, source=rawtext.source, source_config=source_config)
            
            if not normalized or not normalized[0].get('content'):
                return Response({"error": "Failed to fetch content from YouTube"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            new_content = normalized[0]['content']
            
            # Update the rawtext
            rawtext.content = normalized[0]['content']
            rawtext.title = normalized[0]['title']
            rawtext.is_updated = True
            rawtext.save()
            
            return Response({"message": "Content redownloaded successfully", "content_length": len(rawtext.content)}, status=status.HTTP_200_OK)
            
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
    serializer_class = TopicTypeSerializer

    def get_queryset(self):
        queryset = TopicType.objects.all().order_by('name')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )
        return queryset

class TopicTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TopicType.objects.all()
    serializer_class = TopicTypeSerializer
    lookup_field = "id"


class AnalyticalFrameworkListView(generics.ListAPIView):
    queryset = AnalyticalFramework.objects.all().order_by("name")
    serializer_class = AnalyticalFrameworkSerializer


class AnalyticalCategoryListView(generics.ListAPIView):
    serializer_class = AnalyticalCategorySerializer

    def get_queryset(self):
        qs = AnalyticalCategory.objects.all().select_related("framework").order_by("framework", "name")
        framework = self.request.query_params.get("framework", "").strip()
        if framework:
            qs = qs.filter(framework__slug=framework)
        return qs


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

def _topic_type_id_exists(pk):
    """True if TopicType with this pk exists (avoids stale AI suggestion IDs)."""
    if pk is None:
        return False
    try:
        pk = int(pk)
    except (TypeError, ValueError):
        return False
    return TopicType.objects.filter(pk=pk).exists()


class TopicCreateView(generics.CreateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

    def get_serializer(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None:
            data = dict(data) if hasattr(data, "items") else data
            tid = data.get("topic_type_id")
            if tid is not None and not _topic_type_id_exists(tid):
                data = dict(data)
                data["topic_type_id"] = None
            kwargs["data"] = data
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        related_ids = self.request.data.get('related_ids', [])
        instance = serializer.save()
        if related_ids:
            instance.related_topics.set(related_ids)
        swot_category_id = self.request.data.get("swot_category_id")
        if swot_category_id is not None:
            cat = AnalyticalCategory.objects.filter(
                id=swot_category_id,
                framework__slug="swot",
            ).first()
            if cat:
                TopicAnalyticalCategory.objects.get_or_create(
                    topic=instance,
                    analytical_category=cat,
                )
        pestel_category_ids = self.request.data.get("pestel_category_ids", [])
        if pestel_category_ids:
            for cat in AnalyticalCategory.objects.filter(
                id__in=pestel_category_ids,
                framework__slug="pestel",
            ):
                TopicAnalyticalCategory.objects.get_or_create(
                    topic=instance,
                    analytical_category=cat,
                )

class TopicDetailView(generics.RetrieveUpdateAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Sanitize topic_type_id if it doesn't exist (e.g. stale AI suggestion)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if getattr(data, "_mutable", None) is False:
            data._mutable = True
        tid = data.get("topic_type_id")
        if tid is not None and not _topic_type_id_exists(tid):
            data["topic_type_id"] = None
        
        # Handle related_ids and school_ids if provided
        related_ids = data.get('related_ids')
        school_ids = data.get('school_ids')
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if related_ids is not None:
            instance.related_topics.set(related_ids)
        if school_ids is not None:
            instance.schools_of_thought.set(school_ids)
            from narratives.utils.school_of_thought import ensure_school_topics_have_type
            ensure_school_topics_have_type(school_ids)

        # Analytical classification: SWOT (0 or 1) and PESTEL (0 or more)
        swot_category_id = data.get("swot_category_id")
        if swot_category_id is not None:
            instance.analytical_categories.filter(
                analytical_category__framework__slug="swot",
            ).delete()
            cat = AnalyticalCategory.objects.filter(
                id=swot_category_id,
                framework__slug="swot",
            ).first()
            if cat:
                TopicAnalyticalCategory.objects.get_or_create(
                    topic=instance,
                    analytical_category=cat,
                )
        pestel_category_ids = data.get("pestel_category_ids")
        if pestel_category_ids is not None:
            instance.analytical_categories.filter(
                analytical_category__framework__slug="pestel",
            ).delete()
            pestel_cats = AnalyticalCategory.objects.filter(
                id__in=pestel_category_ids,
                framework__slug="pestel",
            )
            for cat in pestel_cats:
                TopicAnalyticalCategory.objects.get_or_create(
                    topic=instance,
                    analytical_category=cat,
                )

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

def _normalise_topic_name_for_match(s):
    """Normalise for duplicate check: lower, collapse spaces, remove middle initials (e.g. 'Donald J Trump' -> 'donald trump')."""
    if not s or not isinstance(s, str):
        return ""
    s = re.sub(r"\s+", " ", s.lower().strip())
    # Remove single-letter "middle" tokens (middle initials)
    s = re.sub(r"\b\s+[a-z]\s+\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class RawTextAISuggestTopicsView(APIView):
    def post(self, request, id):
        rawtext = get_object_or_404(RawText, id=id)
        
        # 1. Topics already linked to this text
        existing_linked_topic_ids = PendingTopic.objects.filter(rawtext=rawtext).values_list('topic_id', flat=True)
        existing_topics_map = {t.name.lower(): t for t in Topic.objects.filter(id__in=existing_linked_topic_ids)}
        
        # 2. All topics in DB (name + alternative_name) so we don't suggest duplicates and can match "Donald J Trump" -> "Donald Trump"
        all_topics = list(Topic.objects.values("id", "name", "alternative_name"))
        all_names_for_ai = set()  # exact strings to pass to AI (do not suggest)
        norm_to_topic = {}  # normalised string -> first topic (for matching)
        for t in all_topics:
            name = (t.get("name") or "").strip()
            alt = (t.get("alternative_name") or "").strip()
            if name:
                all_names_for_ai.add(name)
                norm_to_topic[_normalise_topic_name_for_match(name)] = t
            if alt:
                all_names_for_ai.add(alt)
                norm_to_topic[_normalise_topic_name_for_match(alt)] = t
        existing_topic_names = list(all_names_for_ai)  # AI gets full DB list so it doesn't suggest "Donald Trump" again
        
        # 3. Hybrid Extraction: spaCy NER + Local AI
        
        # 3a. spaCy NER (PERSON, ORG)
        from narratives.utils.ai_module import extract_entities_with_spacy
        spacy_entities = extract_entities_with_spacy(rawtext.content)
        
        # 3b. Local AI (Abstract concepts) — pass actual topic types + all existing names/alt names
        from narratives.utils.local_ai import suggest_new_topics_with_ai
        topic_types_for_ai = list(
            TopicType.objects.values("id", "name").order_by("name")
        )
        ai_results = suggest_new_topics_with_ai(
            rawtext.content[:4000], existing_topic_names, topic_types_for_ai
        )
        
        if not ai_results or "suggested_topics" not in ai_results:
            return Response({"error": "AI failed to suggest topics."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        ai_suggestions = ai_results["suggested_topics"]
        # Build name -> TopicType lookup for resolving type_name to id (case-insensitive)
        type_by_name = {tt["name"].lower(): tt for tt in topic_types_for_ai}
        
        # 3. Merge and Filter suggestions
        # We'll use a dict keyed by lowercase name to deduplicate
        merged_suggestions = {} # name_lower -> {name, type_id, type_name, is_ner}
        
        # Add NER entities first (higher confidence for specific names)
        for ent in spacy_entities:
            name_lower = ent["name"].lower()
            merged_suggestions[name_lower] = {
                "name": ent["name"],
                "suggested_type_id": ent.get("suggested_type_id"),
                "suggested_type_name": ent.get("suggested_type_name"),
                "is_ner": True
            }
        
        # Add AI suggestions (support both list of objects {name, type_name} and legacy list of strings)
        for item in ai_suggestions:
            if isinstance(item, str):
                name = item.strip()
                type_name = None
            else:
                name = (item.get("name") or "").strip()
                type_name = item.get("type_name")
            if not name:
                continue
            name_lower = name.lower()
            if name_lower not in merged_suggestions:
                suggested_type_id = None
                suggested_type_name = None
                if type_name and isinstance(type_name, str):
                    tt = type_by_name.get(type_name.strip().lower())
                    if tt:
                        suggested_type_id = tt["id"]
                        suggested_type_name = tt["name"]
                merged_suggestions[name_lower] = {
                    "name": name,
                    "suggested_type_id": suggested_type_id,
                    "suggested_type_name": suggested_type_name,
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
            
            # Check if already linked to THIS article (by name or by topic we'll resolve to)
            is_already_linked = name_lower in existing_topics_map
            
            # Check if already exists in DB: by name, alternative_name, or normalised form (e.g. "Donald J Trump" -> "Donald Trump", "AI" <-> "Artificial Intelligence")
            topic_obj = Topic.objects.filter(Q(name__iexact=name) | Q(alternative_name__iexact=name)).first()
            if not topic_obj:
                norm = _normalise_topic_name_for_match(name)
                if norm:
                    t = norm_to_topic.get(norm)
                    if t:
                        topic_obj = Topic.objects.filter(id=t["id"]).first()
            
            if topic_obj and topic_obj.id in existing_linked_topic_ids:
                is_already_linked = True

            # Skip suggestions already linked to this rawtext (e.g. already in Suggested Topics / keywords below)
            if is_already_linked:
                rejected_suggestions.append({"name": name, "reason": "Already linked to this text"})
                continue
            
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
                # Use canonical topic name so UI shows "Donald Trump" not "Donald J Trump"
                name = topic_obj.name

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
                title = pt.rawtext.title or ""
                matched = pt.matched_keyword or topic.name
                if matched and topic_title_matches_keyword(topic, matched, title):
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
        from narratives.utils.school_of_thought import ensure_school_topics_have_type
        school_ids_added = []
        for s_name in ai_results.get("schools", []):
            s_topic = get_or_create_topic(s_name, "schools")
            if s_topic and s_topic != topic:
                topic.schools_of_thought.add(s_topic)
                linked_schools.append(s_name)
                school_ids_added.append(s_topic.id)
        if school_ids_added:
            ensure_school_topics_have_type(school_ids_added)

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
            from narratives.utils.school_of_thought import ensure_school_topics_have_type
            ensure_school_topics_have_type(new_school_ids)

        # 2. Merge Keywords (strong can be string or dict with 'keyword')
        def kw_key(entry):
            return entry if isinstance(entry, str) else entry.get("keyword")
        seen_strong = {kw_key(k) for k in target.keywords}
        merged_strong = list(target.keywords)
        for kw in source.keywords:
            k = kw_key(kw)
            if k and k not in seen_strong:
                seen_strong.add(k)
                merged_strong.append(kw)
        target.keywords = merged_strong

        # Merge weak keywords (avoid duplicates by keyword string)
        weak_kws_map = {w.get('keyword'): w for w in target.weak_keywords if w.get('keyword')}
        for w in source.weak_keywords:
            k = w.get('keyword')
            if k and k not in weak_kws_map:
                weak_kws_map[k] = w
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

class TopicAggregatedDetailView(APIView):
    """
    Returns a combined payload for the Topic Detail page to reduce round-trips.
    Includes: topic details, distribution data, and latest mentions.
    """
    def get(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        
        # 1. Topic basic data
        topic_data = TopicSerializer(topic).data
        
        # 2. Distribution data (logic from TopicDistributionView)
        pending_topics = PendingTopic.objects.filter(
            topic=topic,
            status="approved",
        ).select_related('rawtext', 'topic')

        total_weight = 0
        title_weight_given = set()
        
        # Mentions for the UI
        mentions = []
        
        for pt in pending_topics:
            rawtext_id = pt.rawtext_id
            weight = 1
            if (rawtext_id, topic.id) not in title_weight_given:
                title = pt.rawtext.title or ""
                matched = pt.matched_keyword or topic.name
                if matched and topic_title_matches_keyword(topic, matched, title):
                    weight = 10
                    title_weight_given.add((rawtext_id, topic.id))
            
            total_weight += weight
            
            # Add to mentions list (limit to latest 10 for the aggregated view)
            if len(mentions) < 10:
                mentions.append({
                    "id": pt.rawtext.id,
                    "title": pt.rawtext.title,
                    "published_at": pt.rawtext.published_at,
                    "matched_keyword": pt.matched_keyword,
                    "context": pt.context
                })

        return Response({
            "topic": topic_data,
            "distribution": {
                "id": topic.id,
                "name": topic.name,
                "total_weight": total_weight,
                "breakdown": [{"id": None, "name": "Direct Mentions", "weight": total_weight}]
            },
            "latest_mentions": mentions
        })

class TopicSuggestMergeView(APIView):
    """
    Uses trigram similarity to find potential topic merges.
    Checks name, alternative_name, and keywords.
    """
    def post(self, request):
        # 1. Get all topics (excluding placeholders)
        topics = Topic.objects.filter(is_placeholder=False)
        
        # 2. Iterate and find pairs with similar names or keywords
        # This is a bit heavy for a single request if there are thousands of topics,
        # but for a few hundred/thousand it's manageable.
        
        # We'll use a more efficient approach: 
        # Pick a random topic and find its most similar counterparts.
        import random
        count = topics.count()
        if count < 2:
            return Response({"message": "Not enough topics to suggest a merge."}, status=status.HTTP_200_OK)
            
        # Try a few random topics to find a good match
        for _ in range(10):
            random_idx = random.randint(0, count - 1)
            source = topics[random_idx]
            
            # Find similar by name or alt_name
            similar = Topic.objects.filter(is_placeholder=False).exclude(id=source.id).annotate(
                similarity=TrigramSimilarity('name', source.name) + 
                           TrigramSimilarity('alternative_name', source.name)
            ).filter(similarity__gt=0.3).order_by('-similarity').first()
            
            if similar:
                return Response({
                    "source_topic": {"id": source.id, "name": source.name},
                    "target_topic": {"id": similar.id, "name": similar.name},
                    "reason": f"High name similarity ({similar.similarity:.2f}). Possible duplicate or synonym."
                }, status=status.HTTP_200_OK)
                
            # Find by keyword overlap (keywords can be string or dict)
            def norm_kw(k):
                return (k if isinstance(k, str) else k.get('keyword', '')).lower()
            source_kws = set(norm_kw(k) for k in source.keywords if norm_kw(k))
            if source_kws:
                for other in topics.exclude(id=source.id).order_by('-updated_at')[:50]:
                    other_kws = set(norm_kw(k) for k in other.keywords if norm_kw(k))
                    overlap = source_kws.intersection(other_kws)
                    if len(overlap) >= 2: # At least 2 overlapping keywords
                        return Response({
                            "source_topic": {"id": source.id, "name": source.name},
                            "target_topic": {"id": other.id, "name": other.name},
                            "reason": f"Keyword overlap: {', '.join(list(overlap)[:3])}. These topics share multiple keywords."
                        }, status=status.HTTP_200_OK)

        return Response({"message": "No obvious merge suggestions found. Try again!"}, status=status.HTTP_200_OK)

class EpochListView(generics.ListCreateAPIView):
    queryset = Epoch.objects.all().order_by('typical_start_date')
    serializer_class = EpochSerializer

class EpochDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Epoch.objects.all()
    serializer_class = EpochSerializer
    lookup_field = "id"
