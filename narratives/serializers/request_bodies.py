from rest_framework import serializers

class ClaimCreateRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    submitter = serializers.CharField(required=False)

class GenerateClaimsRequestSerializer(serializers.Serializer):
    text = serializers.CharField()

class MarketCreateRequestSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()

class MarketBuyRequestSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()
    side = serializers.ChoiceField(choices=["TRUE", "FALSE"])
    amount = serializers.CharField()

class RawTextDuplicateCheckRequestSerializer(serializers.Serializer):
    content = serializers.CharField()
