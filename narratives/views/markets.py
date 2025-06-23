from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from decimal import Decimal
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema

from ..models import Market, Claim, UserAccount, MarketPosition, VerificationStatus
from ..serializers import MarketSerializer
from ..serializers.request_bodies import MarketCreateRequestSerializer, MarketBuyRequestSerializer

class MarketCreateView(APIView):

    @swagger_auto_schema(request_body=MarketCreateRequestSerializer, responses={201: "Market created"})
    def post(self, request, claim_id):
        claim = get_object_or_404(Claim, id=claim_id)

        if claim.verification_status.name not in ["ai_reviewed", "ai_variants_generated"]:
            return Response({"error": "Claim must be AI-verified before market creation."}, status=status.HTTP_400_BAD_REQUEST)

        wallet_address = request.data.get("wallet_address")
        if not wallet_address:
            return Response({"error": "Wallet address is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_market = Market.objects.filter(claim=claim).first()
        if existing_market:
            return Response({"error": "Market already exists for this claim."}, status=status.HTTP_400_BAD_REQUEST)

        time_since_creation = now() - claim.created_at
        exclusive_to_author = time_since_creation <= timedelta(minutes=30)

        if exclusive_to_author and claim.author != wallet_address:
            return Response({"error": "Only the claim's author can create a market within 30 minutes of submission."}, status=status.HTTP_403_FORBIDDEN)

        market_created_status = get_object_or_404(VerificationStatus, name="market_created")

        market = Market.objects.create(
            claim=claim,
            creator=wallet_address
        )

        claim.verification_status = market_created_status
        claim.status_description = "Market has been created for this claim."
        claim.save()

        return Response({"message": "Market created successfully.", "market_id": market.id, "claim_slug": claim.slug}, status=status.HTTP_201_CREATED)

class MarketListView(APIView):
    def get(self, request):
        markets = Market.objects.all().order_by('-created_at')
        serializer = MarketSerializer(markets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MarketBuyView(APIView):

    @swagger_auto_schema(request_body=MarketBuyRequestSerializer, responses={200: "Shares purchased"})
    def post(self, request, market_id):
        side = request.data.get("side")
        amount_str = request.data.get("amount")
        wallet_address = request.data.get("wallet_address")

        if not all([side, amount_str, wallet_address]):
            return Response({"error": "side, amount, and wallet_address are required."}, status=status.HTTP_400_BAD_REQUEST)

        if side not in ["TRUE", "FALSE"]:
            return Response({"error": "Invalid side choice."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            requested_shares = Decimal(amount_str)
            if requested_shares <= 0:
                raise ValueError
        except:
            return Response({"error": "Amount must be a positive numeric value."}, status=status.HTTP_400_BAD_REQUEST)

        market = get_object_or_404(Market, id=market_id)
        user_account = get_object_or_404(UserAccount, wallet_address=wallet_address)

        try:
            existing_position = MarketPosition.objects.get(user=user_account, market=market)
            if existing_position.side != side:
                return Response(
                    {"error": "You already hold the opposite side. Please sell first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            position = existing_position
        except MarketPosition.DoesNotExist:
            position = None

        cost = market.cost_to_buy_linear(side, requested_shares)

        if user_account.balance < cost:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        user_account.balance -= cost
        user_account.save()

        if side == "TRUE":
            if market.true_shares_remaining < requested_shares:
                return Response({"error": "Not enough TRUE shares available."}, status=status.HTTP_400_BAD_REQUEST)
            market.true_shares_remaining -= requested_shares
        else:
            if market.false_shares_remaining < requested_shares:
                return Response({"error": "Not enough FALSE shares available."}, status=status.HTTP_400_BAD_REQUEST)
            market.false_shares_remaining -= requested_shares

        market.save()

        if position is None:
            position = MarketPosition.objects.create(
                user=user_account,
                market=market,
                side=side,
                shares=requested_shares,
                cost_basis=cost
            )
        else:
            position.shares += requested_shares
            position.cost_basis += cost
            position.save()

        return Response({
            "message": "Shares purchased successfully via bonding curve.",
            "position_id": position.id,
            "side": side,
            "shares_bought": str(requested_shares),
            "total_cost": str(cost),
            "new_total_shares": str(position.shares),
            "remaining_true": str(market.true_shares_remaining),
            "remaining_false": str(market.false_shares_remaining),
            "updated_balance": str(user_account.balance),
        }, status=status.HTTP_200_OK)
