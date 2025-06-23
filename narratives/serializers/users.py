from rest_framework import serializers
from ..models import UserAccount

class UserAccountSerializer(serializers.ModelSerializer):
    verification_status_name = serializers.ReadOnlyField(source="verification_status.name")
    balance = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = UserAccount
        fields = ["wallet_address", "verification_status_name", "balance", "created_at"]
        read_only_fields = ["wallet_address", "balance", "verification_status_name", "created_at"]
