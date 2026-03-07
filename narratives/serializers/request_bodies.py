from rest_framework import serializers

class MarketCreateRequestSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()

class MarketBuyRequestSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()
    side = serializers.ChoiceField(choices=["TRUE", "FALSE"])
    amount = serializers.CharField()

class RawTextDuplicateCheckRequestSerializer(serializers.Serializer):
    content = serializers.CharField()
