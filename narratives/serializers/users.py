from rest_framework import serializers
from ..models import UserAccount

class UserAccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = UserAccount
        fields = ["wallet_address", "balance", "created_at"]
        read_only_fields = ["wallet_address", "balance", "created_at"]
