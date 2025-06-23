from rest_framework import serializers
from ..models import Claim, Person

class ClaimSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    verification_status_display = serializers.CharField(source="verification_status.get_name_display", read_only=True)
    parent_claim = serializers.PrimaryKeyRelatedField(queryset=Claim.objects.all(), allow_null=True, required=False)
    attributed_persons = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), many=True, required=False
    )

    class Meta:
        model = Claim
        fields = [
            "id",
            "slug",
            "text",
            "verification_status",
            "verification_status_name",
            "verification_status_display",
            "status_description",
            "submitter",
            "attributed_persons",
            "parent_claim",
            "generated_by_ai",
            "ai_model",
            "content_fingerprint",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "id", "slug", "verification_status_name", "verification_status_display",
            "content_fingerprint", "created_at", "updated_at"
        ]
