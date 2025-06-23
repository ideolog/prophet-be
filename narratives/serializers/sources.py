from rest_framework import serializers
from ..models import RawText
from narratives.utils.text import generate_fingerprint

class RawTextSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_blank=True)
    subtitle = serializers.CharField(required=False, allow_blank=True)
    author = serializers.PrimaryKeyRelatedField(
        queryset=RawText._meta.get_field('author').related_model.objects.all(),
        allow_null=True, required=False
    )
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(
        queryset=RawText._meta.get_field('source').related_model.objects.all()
    )
    genre = serializers.PrimaryKeyRelatedField(
        queryset=RawText._meta.get_field('genre').related_model.objects.all(),
        allow_null=True, required=False
    )

    class Meta:
        model = RawText
        fields = [
            "id", "title", "subtitle", "author", "published_at",
            "content", "slug", "content_fingerprint", "source", "genre"
        ]
        read_only_fields = ["id", "slug", "content_fingerprint"]

    def create(self, validated_data):
        content = validated_data.get("content")
        if content and not validated_data.get("content_fingerprint"):
            validated_data["content_fingerprint"] = generate_fingerprint(content)
        return super().create(validated_data)
