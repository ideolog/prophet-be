from django.db.models import Count
from rest_framework import serializers
from ..models import RawText, Source, Topic, PendingTopic, TopicType, Epoch, AnalyticalFramework, AnalyticalCategory
from narratives.models.categories import DeclinedTopic
from narratives.utils.text import generate_fingerprint, title_contains_keyword_as_word, topic_title_matches_keyword, parse_keyword_spec
from narratives.utils.topic_name_censor import is_forbidden_topic_name

class AnalyticalFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticalFramework
        fields = ["id", "name", "slug"]


class AnalyticalCategorySerializer(serializers.ModelSerializer):
    framework_id = serializers.IntegerField(source="framework.id", read_only=True)

    class Meta:
        model = AnalyticalCategory
        fields = ["id", "name", "slug", "framework_id"]


class TopicTypeSerializer(serializers.ModelSerializer):
    topics_count = serializers.IntegerField(source='topics.count', read_only=True)
    parent = serializers.SerializerMethodField()
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=TopicType.objects.all(),
        source='parent',
        required=False,
        allow_null=True
    )

    class Meta:
        model = TopicType
        fields = ["id", "name", "slug", "description", "parent", "parent_id", "is_swot", "updated_at", "topics_count"]

    def get_parent(self, obj):
        if obj.parent_id is None:
            return None
        return {"id": obj.parent.id, "name": obj.parent.name}

class TopicSerializer(serializers.ModelSerializer):
    related_count = serializers.IntegerField(source='related_topics.count', read_only=True)
    keywords_count = serializers.SerializerMethodField()
    mentions_count = serializers.IntegerField(read_only=True, default=0)
    related_topics = serializers.SerializerMethodField()
    schools_of_thought = serializers.SerializerMethodField()
    topics_in_school = serializers.SerializerMethodField()
    topic_type = serializers.SerializerMethodField()
    topic_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TopicType.objects.all(),
        source='topic_type',
        required=False,
        allow_null=True
    )
    swot_category = serializers.SerializerMethodField()
    pestel_categories = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "name", "alternative_name", "slug", "description", "keywords", "weak_keywords", "metadata",
            "wikipedia_url", "is_placeholder", "updated_at",
            "related_count", "keywords_count", "mentions_count",
            "related_topics", "schools_of_thought", "topics_in_school",
            "topic_type", "topic_type_id",
            "swot_category", "pestel_categories",
        ]

    def get_topic_type(self, obj):
        if obj.topic_type:
            return {"id": obj.topic_type.id, "name": obj.topic_type.name}
        return None

    def get_swot_category(self, obj):
        link = obj.analytical_categories.filter(
            analytical_category__framework__slug="swot",
        ).select_related("analytical_category").first()
        if link:
            c = link.analytical_category
            return {"id": c.id, "name": c.name}
        return None

    def get_pestel_categories(self, obj):
        links = obj.analytical_categories.filter(
            analytical_category__framework__slug="pestel",
        ).select_related("analytical_category").order_by("analytical_category__name")
        return [{"id": l.analytical_category.id, "name": l.analytical_category.name} for l in links]

    def get_keywords_count(self, obj):
        try:
            count = len(obj.keywords) if isinstance(obj.keywords, list) else 0
            count += len(obj.weak_keywords) if isinstance(obj.weak_keywords, list) else 0
            return count
        except:
            return 0

    def get_related_topics(self, obj):
        try:
            return [{"id": r.id, "name": r.name} for r in obj.related_topics.all()]
        except:
            return []

    def get_schools_of_thought(self, obj):
        try:
            return [{"id": s.id, "name": s.name} for s in obj.schools_of_thought.all()]
        except:
            return []

    def get_topics_in_school(self, obj):
        # Return topics that have this topic as their school of thought
        try:
            return [{"id": t.id, "name": t.name} for t in obj.topics_in_school.all()]
        except:
            return []

    def validate_name(self, value):
        if not value:
            return value
        name = value.strip()
        if is_forbidden_topic_name(name):
            from ..models.categories import DeclinedTopic
            DeclinedTopic.objects.create(
                name=name,
                source_topic=None,
                target_field="api_create",
                reason="other",
                reason_detail="Forbidden topic name pattern (e.g. source byline like 'Cointelegraph by …'). Topic not created.",
            )
            raise serializers.ValidationError(
                "Topic name is not allowed (forbidden pattern, e.g. source byline)."
            )
        return name

    def validate_keywords(self, value):
        if not isinstance(value, list):
            return value
        result = []
        for entry in value:
            if isinstance(entry, str):
                s = entry.strip()
                if s and (s.startswith('"') or s.startswith("'") or s.startswith('!')):
                    spec = parse_keyword_spec(entry)
                    if spec.get('keyword'):
                        result.append(spec)
                else:
                    result.append(entry)
            else:
                result.append(entry)
        return result

    def validate_weak_keywords(self, value):
        if not isinstance(value, list):
            return value
        result = []
        for obj in value:
            if not isinstance(obj, dict):
                result.append(obj)
                continue
            kw = obj.get('keyword')
            if isinstance(kw, str):
                s = kw.strip()
                if s and (s.startswith('"') or s.startswith("'") or s.startswith('!')):
                    spec = parse_keyword_spec(kw)
                    result.append({**obj, 'keyword': spec.get('keyword', kw), 'whole_word_only': spec.get('whole_word_only', True), 'case_sensitive': spec.get('case_sensitive', False)})
                else:
                    result.append(obj)
            else:
                result.append(obj)
        return result

class PendingTopicSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = PendingTopic
        fields = ["id", "topic", "topic_name", "matched_keyword", "is_weak", "found_context_words", "context", "status", "found_in", "weight", "swot_analysis", "created_at"]
        read_only_fields = ["id", "created_at"]

class SourceSerializer(serializers.ModelSerializer):
    topic_distribution = serializers.SerializerMethodField()

    class Meta:
        model = Source
        fields = [
            "id", "name", "platform", "handle", "external_id",
            "description", "subscriber_count", "avatar_url", "avatar_file",
            "topic", "url",
            "rss_url", "timezone", "slug", "is_new", "created_at",
            "topic_distribution",
        ]
        read_only_fields = ["id", "slug", "created_at"]

    def get_topic_distribution(self, obj):
        from django.db.models import Case, When, Value, IntegerField, Sum
        from narratives.models import PendingTopic, Topic

        # 1. Get all approved pending topics for this source
        pending_topics = PendingTopic.objects.filter(
            rawtext__source=obj,
            status="approved",
        ).select_related('rawtext', 'topic')

        if not pending_topics.exists():
            return []

        # 2. Calculate weights for each topic mention
        topic_weights = {}
        # Track if we've already given the title weight for a topic in a specific article
        title_weight_given = set() # (rawtext_id, topic_id)

        for pt in pending_topics:
            topic_id = pt.topic_id
            topic_name = pt.topic.name
            rawtext_id = pt.rawtext_id
            
            # Default weight is 1 (content)
            weight = 1
            
            # Title weight uses same rules as content (whole_word_only / case_sensitive from topic keywords)
            if (rawtext_id, topic_id) not in title_weight_given:
                title = pt.rawtext.title or ""
                matched = pt.matched_keyword or topic_name
                topic_obj = pt.topic
                if matched and topic_title_matches_keyword(topic_obj, matched, title):
                    weight = 10
                    title_weight_given.add((rawtext_id, topic_id))
            
            if topic_id not in topic_weights:
                topic_weights[topic_id] = {
                    "name": topic_name, 
                    "weight": 0,
                    "type": pt.topic.topic_type.name if pt.topic.topic_type else None
                }
            
            topic_weights[topic_id]["weight"] += weight

        # 3. Format for response
        result = []
        for topic_id, info in topic_weights.items():
            result.append({
                "id": topic_id,
                "name": info["name"],
                "total_weight": info["weight"],
                "type": info["type"]
            })

        # Sort by total weight
        result.sort(key=lambda x: x["total_weight"], reverse=True)
        return result

class RawTextSerializer(serializers.ModelSerializer):
    categorization_status = serializers.ReadOnlyField()
    current_system_version = serializers.SerializerMethodField()
    title = serializers.CharField(required=False, allow_blank=True)
    subtitle = serializers.CharField(required=False, allow_blank=True)
    author = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    genre = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    pending_topics = PendingTopicSerializer(many=True, read_only=True)
    topic_weights = serializers.SerializerMethodField()

    class Meta:
        model = RawText
        fields = [
            "id", "title", "subtitle", "author", "published_at",
            "content", "slug", "content_fingerprint", "source", "genre",
            "categorization_status", "categorization_version", "current_system_version", "last_categorized_at",
            "is_new", "is_updated", "created_at", "source_url",
            "pending_topics", "topic_weights", "ai_suggestions"
        ]

    def get_topic_weights(self, obj):
        """Weights per topic for this rawtext (title bonus uses same rules as content)."""
        from narratives.models import PendingTopic
        pending_topics = PendingTopic.objects.filter(rawtext=obj, status="approved").select_related("topic")
        if not pending_topics.exists():
            return []
        title_weight_given = set()
        topic_weights = {}
        for pt in pending_topics:
            topic_id = pt.topic_id
            topic_name = pt.topic.name
            weight = 1
            if (obj.id, topic_id) not in title_weight_given:
                title = obj.title or ""
                matched = pt.matched_keyword or topic_name
                if matched and topic_title_matches_keyword(pt.topic, matched, title):
                    weight = 10
                    title_weight_given.add((obj.id, topic_id))
            if topic_id not in topic_weights:
                topic_weights[topic_id] = {"id": topic_id, "name": topic_name, "weight": 0}
            topic_weights[topic_id]["weight"] += weight
        return list(topic_weights.values())

    def get_current_system_version(self, obj):
        from ..models.categories import AppConfiguration
        return AppConfiguration.get_version("categorization_version")

    def get_author(self, obj):
        if obj.author:
            return {"id": obj.author.id, "name": obj.author.name}
        return None

    def get_source(self, obj):
        if obj.source:
            return {"id": obj.source.id, "name": obj.source.name, "platform": obj.source.platform}
        return None

    def get_genre(self, obj):
        if obj.genre:
            return {"id": obj.genre.id, "name": obj.genre.name}
        return None

    def create(self, validated_data):
        content = validated_data.get("content")
        if content and not validated_data.get("content_fingerprint"):
            validated_data["content_fingerprint"] = generate_fingerprint(content)
        return super().create(validated_data)

class DeclinedTopicSerializer(serializers.ModelSerializer):
    source_topic_name = serializers.CharField(source='source_topic.name', read_only=True)

    class Meta:
        model = DeclinedTopic
        fields = [
            "id", "name", "source_topic", "source_topic_name", 
            "target_field", "reason", "reason_detail", "created_at"
        ]
        read_only_fields = ["id", "created_at"]

class EpochSerializer(serializers.ModelSerializer):
    topic_id = serializers.IntegerField(source='topic.id', read_only=True)
    class Meta:
        model = Epoch
        fields = [
            "id", "name", "slug", "description", 
            "notes_on_periodization", "source_summary", "topic_id",
            "earliest_start_date", "typical_start_date", "core_start_date",
            "core_end_date", "typical_end_date", "latest_end_date"
        ]
        read_only_fields = ["id", "slug"]
