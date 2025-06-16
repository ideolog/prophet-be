from rest_framework import serializers
from ..models import RawText

class RawTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawText
        fields = [
            "id", "title", "subtitle", "author", "published_at",
            "content", "slug", "content_fingerprint", "source", "genre"
        ]
