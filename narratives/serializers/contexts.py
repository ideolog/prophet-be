# narratives/serializers/contexts.py
from rest_framework import serializers
from narratives.models import ContextSet


class ContextSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContextSet
        fields = ["id", "slug", "name", "words", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_slug(self, value):
        if value and not value.replace("_", "").isalnum():
            raise serializers.ValidationError("Slug should be alphanumeric (underscores allowed), e.g. CRYPTO_WEAK_CONTEXT")
        return value

    def validate_words(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("words must be a list of strings")
        return [str(w).strip() for w in value if str(w).strip()]
