from rest_framework import serializers
from .models import Claim, Market, UserAccount, MarketPosition, RawText

class RawTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawText
        fields = '__all__'

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
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    balance = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)  # Add balance

    class Meta:
        model = UserAccount
        fields = ["wallet_address", "verification_status_name", "balance", "created_at"]


# serializers.py
class MarketPositionSerializer(serializers.ModelSerializer):
    claim_text = serializers.CharField(source="market.claim.text", read_only=True)
    claim_slug = serializers.CharField(source="market.claim.slug", read_only=True)
    total_shares = serializers.SerializerMethodField()  # NEW FIELD for total market shares

    class Meta:
        model = MarketPosition
        fields = ["claim_text", "claim_slug", "side", "shares", "cost_basis", "total_shares"]

    def get_total_shares(self, obj):
        """Returns the total shares in the market for the given side."""
        if obj.side == "TRUE":
            return Market.objects.get(id=obj.market.id).true_shares_remaining
        else:
            return Market.objects.get(id=obj.market.id).false_shares_remaining


    def get_side_display(self, obj):
        """Returns 'TRUE' in green or 'FALSE' in red."""
        return f"<span style='color: {'green' if obj.side == 'TRUE' else 'red'}'>{obj.side}</span>"

    def get_shares_percentage(self, obj):
        """Calculate the percentage of shares the user holds in this market."""
        total_shares = obj.market.true_shares_remaining + obj.market.false_shares_remaining
        if total_shares > 0:
            return round((obj.shares / total_shares) * 100, 2)
        return 0.0

    def get_yield_value(self, obj):
        """Placeholder: Always return 0 for now."""
        return 0.0
