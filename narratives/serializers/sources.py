from rest_framework import serializers
from ..models import RawText, Source
from narratives.utils.text import generate_fingerprint

class TopicSerializer(serializers.ModelSerializer):
    parents_count = serializers.IntegerField(source='parents.count', read_only=True)
    sub_topics_count = serializers.IntegerField(source='sub_topics.count', read_only=True)
    keywords_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "name", "slug", "description", "keywords", 
            "parents_count", "sub_topics_count", "keywords_count", "level"
        ]

    def get_keywords_count(self, obj):
        return len(obj.keywords) if isinstance(obj.keywords, list) else 0

    def get_level(self, obj):
        # Level 0 if no parents, else 1 (simplified for now)
        return 0 if obj.parents.count() == 0 else 1

class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            "id", "name", "platform", "handle", "external_id", 
            "description", "subscriber_count", "avatar_url", "avatar_file",
            "topic", "owner_person", "owner_organization", "url", 
            "rss_url", "timezone", "slug", "is_new", "created_at"
        ]
        read_only_fields = ["id", "slug", "created_at"]

class RawTextSerializer(serializers.ModelSerializer):
    is_processed = serializers.SerializerMethodField()
    title = serializers.CharField(required=False, allow_blank=True)
    subtitle = serializers.CharField(required=False, allow_blank=True)
    author = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    genre = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = RawText
        fields = [
            "id", "title", "subtitle", "author", "published_at",
            "content", "slug", "content_fingerprint", "source", "genre",
            "is_processed", "is_new", "is_updated", "created_at", "source_url"
        ]
        read_only_fields = ["id", "slug", "content_fingerprint", "is_processed", "is_new", "is_updated", "created_at"]

    def get_is_processed(self, obj):
        return obj.processing_records.filter(status='SUCCESS').exists()

    def get_author(self, obj):
        if obj.author:
            return {"id": obj.author.id, "name": obj.author.full_name}
        return None

    def get_source(self, obj):
        if obj.source:
            return {"id": obj.source.id, "name": obj.source.name, "platform": obj.source.platform}
        return None

    def get_genre(self, obj):
        if obj.genre:
            return {"id": obj.genre.id, "name": obj.genre.name}
        return None

    def get_is_processed(self, obj):
        return obj.processing_records.filter(status='SUCCESS').exists()

    def create(self, validated_data):
        content = validated_data.get("content")
        if content and not validated_data.get("content_fingerprint"):
            validated_data["content_fingerprint"] = generate_fingerprint(content)
        return super().create(validated_data)
