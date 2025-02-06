from rest_framework import serializers
from .models import Claim, Market, Narrative, UserAccount

class MarketSerializer(serializers.ModelSerializer):
    claim_text = serializers.CharField(source="claim.text", read_only=True)
    claim_slug = serializers.CharField(source="claim.slug", read_only=True)
    status = serializers.CharField(source="claim.verification_status.get_name_display", read_only=True)

    # New fields to expose current price per share
    current_true_price = serializers.SerializerMethodField()
    current_false_price = serializers.SerializerMethodField()

    class Meta:
        model = Market
        fields = [
            "id", "creator", "created_at", "claim_text", "claim_slug", "status",
            "true_shares_remaining", "false_shares_remaining",
            "current_true_price", "current_false_price"
        ]

    def get_current_true_price(self, obj):
        return obj.current_price_for_side("TRUE")

    def get_current_false_price(self, obj):
        return obj.current_price_for_side("FALSE")


class ClaimSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    verification_status_display = serializers.CharField(source="verification_status.get_name_display", read_only=True)
    parent_claim = serializers.PrimaryKeyRelatedField(queryset=Claim.objects.all(), allow_null=True, required=False)
    ai_variants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    # Include nested Market data
    market = MarketSerializer(read_only=True)

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
            "author",
            "parent_claim",
            "ai_variants",
            "market",
        ]

class UserAccountSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source='verification_status.name', read_only=True)

    class Meta:
        model = UserAccount
        fields = ["wallet_address", "verification_status_name", "created_at"]

class NarrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narrative
        fields = ["slug", "description", "modality"]
