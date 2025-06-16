from rest_framework import serializers
from ..models import UserAccount

class UserAccountSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.CharField(source="verification_status.name", read_only=True)
    balance = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = UserAccount
        fields = ["wallet_address", "verification_status_name", "balance", "created_at"]
