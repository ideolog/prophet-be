from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import UserAccount, MarketPosition
from ..serializers import UserAccountSerializer


class WalletLoginView(APIView):
    def post(self, request):
        wallet_address = request.data.get("wallet_address")
        if not wallet_address:
            return Response({"error": "Wallet address is required."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = UserAccount.objects.get_or_create(
            wallet_address=wallet_address
        )

        serializer = UserAccountSerializer(user)
        response_data = serializer.data
        response_data["status"] = "new" if created else "existing"

        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class UserAccountDetailView(APIView):
    def get(self, request, wallet_address):
        user = get_object_or_404(UserAccount, wallet_address=wallet_address)
        serializer = UserAccountSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyPositionsView(APIView):
    def get(self, request, wallet_address):
        return Response([], status=status.HTTP_200_OK)
