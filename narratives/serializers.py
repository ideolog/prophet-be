from rest_framework import serializers
from .models import *

class UserAccountSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source='verification_status.name', read_only=True)
    class Meta:
        model = UserAccount
        fields = ["wallet_address", "verification_status_name", "created_at"]


class ClaimSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    verification_status_display = serializers.CharField(source="verification_status.get_name_display", read_only=True)  # Human-readable
    parent_claim = serializers.PrimaryKeyRelatedField(queryset=Claim.objects.all(), allow_null=True, required=False)
    ai_variants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id", "slug", "text",
            "verification_status", "verification_status_name", "verification_status_display",
            "status_description", "author", "parent_claim", "ai_variants",
        ]


class NarrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narrative
        fields = ['slug', 'description', 'modality']  # You can add more fields if necessary
