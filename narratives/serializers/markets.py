from rest_framework import serializers
from ..models import Market, MarketPosition

class MarketSerializer(serializers.ModelSerializer):
    claim_text = serializers.CharField(source="claim.text", read_only=True)
    claim_slug = serializers.CharField(source="claim.slug", read_only=True)
    status = serializers.CharField(source="claim.verification_status.get_name_display", read_only=True)
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

class MarketPositionSerializer(serializers.ModelSerializer):
    claim_text = serializers.CharField(source="market.claim.text", read_only=True)
    claim_slug = serializers.CharField(source="market.claim.slug", read_only=True)
    total_shares = serializers.SerializerMethodField()

    class Meta:
        model = MarketPosition
        fields = ["claim_text", "claim_slug", "side", "shares", "cost_basis", "total_shares"]

    def get_total_shares(self, obj):
        if obj.side == "TRUE":
            return Market.objects.get(id=obj.market.id).true_shares_remaining
        return Market.objects.get(id=obj.market.id).false_shares_remaining