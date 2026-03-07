from rest_framework import serializers
from ..models import Market, MarketPosition

class MarketSerializer(serializers.ModelSerializer):
    current_true_price = serializers.SerializerMethodField()
    current_false_price = serializers.SerializerMethodField()

    class Meta:
        model = Market
        fields = [
            "id", "creator", "created_at",
            "true_shares_remaining", "false_shares_remaining",
            "current_true_price", "current_false_price"
        ]

    def get_current_true_price(self, obj):
        return obj.current_price_for_side("TRUE")

    def get_current_false_price(self, obj):
        return obj.current_price_for_side("FALSE")


class MarketPositionSerializer(serializers.ModelSerializer):
    total_shares = serializers.SerializerMethodField()

    class Meta:
        model = MarketPosition
        fields = ["side", "shares", "cost_basis", "total_shares"]

    def get_total_shares(self, obj):
        return (
            obj.market.true_shares_remaining
            if obj.side == "TRUE"
            else obj.market.false_shares_remaining
        )
