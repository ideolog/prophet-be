from rest_framework import serializers
from ..models import Claim
from .markets import MarketSerializer  # nested import

class ClaimSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    verification_status_display = serializers.CharField(source="verification_status.get_name_display", read_only=True)
    parent_claim = serializers.PrimaryKeyRelatedField(queryset=Claim.objects.all(), allow_null=True, required=False)
    ai_variants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    market = MarketSerializer(read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id", "slug", "text", "verification_status", "verification_status_name",
            "verification_status_display", "status_description", "author",
            "parent_claim", "ai_variants", "market",
        ]
