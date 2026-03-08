from django.db.models import Count
from rest_framework import serializers
from ..models import RawText, Source, Topic, PendingTopic
from narratives.models.categories import DeclinedTopic
from narratives.utils.text import generate_fingerprint

class TopicSerializer(serializers.ModelSerializer):
    parents_count = serializers.IntegerField(source='parents.count', read_only=True)
    children_count = serializers.IntegerField(source='children.count', read_only=True)
    related_count = serializers.IntegerField(source='related_topics.count', read_only=True)
    keywords_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    related_topics = serializers.SerializerMethodField()
    functions = serializers.SerializerMethodField()
    schools_of_thought = serializers.SerializerMethodField()
    topics_in_school = serializers.SerializerMethodField()
    function_of = serializers.SerializerMethodField()
    topic_type = serializers.SerializerMethodField()
    topic_type_id = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.filter(is_placeholder=True),
        source='topic_type',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Topic
        fields = [
            "id", "name", "alternative_name", "slug", "description", "keywords", "weak_keywords", "metadata",
            "is_placeholder", "updated_at",
            "parents_count", "children_count", "related_count", "keywords_count", "level",
            "parents", "children", "related_topics", "functions", "function_of", "schools_of_thought", "topics_in_school",
            "topic_type", "topic_type_id"
        ]

    def get_topic_type(self, obj):
        if obj.topic_type:
            return {"id": obj.topic_type.id, "name": obj.topic_type.name}
        return None

    def get_keywords_count(self, obj):
        try:
            count = len(obj.keywords) if isinstance(obj.keywords, list) else 0
            count += len(obj.weak_keywords) if isinstance(obj.weak_keywords, list) else 0
            return count
        except:
            return 0

    def get_level(self, obj):
        # Recursive level calculation
        def get_node_level(node, current_level=0, visited=None):
            if visited is None:
                visited = set()
            
            if node.id in visited:
                return current_level
            visited.add(node.id)
            
            parents = node.parents.all()
            if not parents:
                return current_level
            # Return max level of any parent path + 1
            return max(get_node_level(p, current_level + 1, visited) for p in parents)
        
        try:
            return get_node_level(obj)
        except:
            return 999 # Safety for circular refs

    def get_parents(self, obj):
        return [{"id": p.id, "name": p.name} for p in obj.parents.all()]

    def get_children(self, obj):
        return [{"id": s.id, "name": s.name} for s in obj.children.all()]

    def get_related_topics(self, obj):
        return [{"id": r.id, "name": r.name} for r in obj.related_topics.all()]

    def get_functions(self, obj):
        return [{"id": f.id, "name": f.name} for f in obj.functions.all()]

    def get_function_of(self, obj):
        return [{"id": t.id, "name": t.name} for t in obj.function_of.all()]

    def get_schools_of_thought(self, obj):
        return [{"id": s.id, "name": s.name} for s in obj.schools_of_thought.all()]

    def get_topics_in_school(self, obj):
        # Return topics that have this topic as their school of thought
        return [{"id": t.id, "name": t.name} for t in obj.topics_in_school.all()]

class PendingTopicSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = PendingTopic
        fields = ["id", "topic", "topic_name", "matched_keyword", "is_weak", "found_context_words", "context", "status", "created_at"]
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
        rows = PendingTopic.objects.filter(
            rawtext__source=obj,
            status="approved",
        ).values("topic__name").annotate(count=Count("id")).order_by("-count")
        return [
            {"name": r["topic__name"], "count": r["count"]}
            for r in rows
            if r["topic__name"]
        ]

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

    class Meta:
        model = RawText
        fields = [
            "id", "title", "subtitle", "author", "published_at",
            "content", "slug", "content_fingerprint", "source", "genre",
            "categorization_status", "categorization_version", "current_system_version", "last_categorized_at",
            "is_new", "is_updated", "created_at", "source_url",
            "pending_topics"
        ]
        read_only_fields = ["id", "slug", "content_fingerprint", "categorization_status", "categorization_version", "current_system_version", "last_categorized_at", "is_new", "is_updated", "created_at"]

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
