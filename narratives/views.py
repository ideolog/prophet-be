from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from datetime import timedelta
from .models import *
from .serializers import ClaimSerializer, UserAccountSerializer, MarketSerializer
from .ai_module import generate_ai_claims, extract_narrative_claims
# Ensure AI module is imported
import time
import logging
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

class WalletLoginView(APIView):
    def post(self, request):
        wallet_address = request.data.get("wallet_address")
        if not wallet_address:
            return Response({"error": "Wallet address is required."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = UserAccount.objects.get_or_create(
            wallet_address=wallet_address,
            defaults={"verification_status": VerificationStatus.objects.get(name="unverified")}
        )

        serializer = UserAccountSerializer(user)
        response_data = serializer.data
        response_data["status"] = "new" if created else "existing"

        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class ClaimDetailView(APIView):
    def get(self, request, claim_id):
        claim = get_object_or_404(Claim, id=claim_id)
        serializer = ClaimSerializer(claim)
        return Response(serializer.data, status=status.HTTP_200_OK)

from django.db.utils import IntegrityError

class ClaimListCreateView(APIView):
    def get(self, request):
        """
        Returns a filtered list of claims ordered by creation date.
        If 'parent_claim' is provided as a query parameter, only return AI-generated claims for that parent.
        """
        parent_claim_id = request.GET.get("parent_claim")

        if parent_claim_id:
            claims = Claim.objects.filter(parent_claim=parent_claim_id).order_by('-created_at')
        else:
            claims = Claim.objects.all().order_by('-created_at')

        serializer = ClaimSerializer(claims, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        time.sleep(1)  # Simulate delay for testing purposes

        try:
            default_status = VerificationStatus.objects.get(name='unverified')
            pending_ai_status = VerificationStatus.objects.get(name='pending_ai_review')
            rejected_status = VerificationStatus.objects.get(name='rejected')
            ai_verified_status = VerificationStatus.objects.get(name='ai_reviewed')
            ai_variants_status = VerificationStatus.objects.get(name='ai_variants_generated')
        except VerificationStatus.DoesNotExist as e:
            logger.error(f"Missing verification status: {e}")
            return Response(
                {"error": "One or more required verification statuses are missing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


        # Set author of the claim to the wallet address if provided
        ZERO_ADDRESS = "11111111111111111111111111111111"
        wallet_address = request.data.get("author")
        data = request.data.copy()
        data["author"] = wallet_address if wallet_address else ZERO_ADDRESS

        # Set default status for the new claim
        data['verification_status'] = pending_ai_status.id

        serializer = ClaimSerializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                try:
                    # Check if the claim already exists
                    existing_claim = Claim.objects.filter(text=data['text']).first()

                    if existing_claim:
                        # If duplicate, save it as "Rejected"
                        duplicate_claim = serializer.save(
                            verification_status=rejected_status,
                            status_description="Duplicate claim detected."
                        )
                        return Response(
                            ClaimSerializer(duplicate_claim).data,
                            status=status.HTTP_201_CREATED
                        )

                    # Otherwise, process it normally
                    claim = serializer.save()

                    # Generate AI alternatives
                    generate_ai_claims(claim, ai_verified_status)

                    # Update claim status to indicate AI variants exist
                    claim.verification_status = ai_variants_status
                    claim.status_description = "AI-generated alternatives are available."
                    claim.save()

                    return Response(serializer.data, status=status.HTTP_201_CREATED)

                except Exception as e:
                    logger.error(f"Error processing claim: {e}")
                    return Response(
                        {"error": "An unexpected error occurred on the server."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarketCreateView(APIView):
    def post(self, request, claim_id):
        """
        Allows the claim's author to create a market within 30 minutes of claim creation.
        After 30 minutes, anyone with a wallet can create a market.
        """
        claim = get_object_or_404(Claim, id=claim_id)

        # Ensure the claim is AI-verified before allowing market creation
        if claim.verification_status.name not in ["ai_reviewed", "ai_variants_generated"]:
            return Response({"error": "Claim must be AI-verified before market creation."}, status=status.HTTP_400_BAD_REQUEST)

        wallet_address = request.data.get("wallet_address")
        if not wallet_address:
            return Response({"error": "Wallet address is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if a market already exists
        existing_market = Market.objects.filter(claim=claim).first()
        if existing_market:
            return Response({"error": "Market already exists for this claim."}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce 30-minute exclusivity rule
        time_since_creation = now() - claim.created_at
        exclusive_to_author = time_since_creation <= timedelta(minutes=30)

        if exclusive_to_author and claim.author != wallet_address:
            return Response({"error": "Only the claim's author can create a market within 30 minutes of submission."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Fetch "Market Created" status
        market_created_status = get_object_or_404(VerificationStatus, name="market_created")

        # ✅ Create market
        market = Market.objects.create(
            claim=claim,
            creator=wallet_address
        )

        # ✅ Update claim status to "Market Created"
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
    def post(self, request, market_id):
        side = request.data.get("side")
        amount_str = request.data.get("amount")  # Number of shares the user wants to buy
        wallet_address = request.data.get("wallet_address")

        if not all([side, amount_str, wallet_address]):
            return Response(
                {"error": "side, amount, and wallet_address are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if side not in ["TRUE", "FALSE"]:
            return Response({"error": "Invalid side choice."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert requested shares to Decimal
        try:
            requested_shares = Decimal(amount_str)
            if requested_shares <= 0:
                raise ValueError
        except:
            return Response({"error": "Amount must be a positive numeric value."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch market and user
        market = get_object_or_404(Market, id=market_id)
        user_account = get_object_or_404(UserAccount, wallet_address=wallet_address)

        # Check if user already holds the opposite side
        try:
            existing_position = MarketPosition.objects.get(user=user_account, market=market)
            if existing_position.side != side:
                return Response(
                    {"error": "You already hold the opposite side. Please sell first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            position = existing_position
        except MarketPosition.DoesNotExist:
            position = None  # No existing position => create later

        # Calculate the total cost using the bonding curve
        cost = market.cost_to_buy_linear(side, requested_shares)

        # **NEW: Check if the user has enough SOL**
        if user_account.balance < cost:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # **NEW: Deduct SOL from user balance**
        user_account.balance -= cost
        user_account.save()

        # Check if enough shares remain
        if side == "TRUE":
            if market.true_shares_remaining < requested_shares:
                return Response({"error": "Not enough TRUE shares available."}, status=status.HTTP_400_BAD_REQUEST)
            market.true_shares_remaining -= requested_shares
        else:  # side == "FALSE"
            if market.false_shares_remaining < requested_shares:
                return Response({"error": "Not enough FALSE shares available."}, status=status.HTTP_400_BAD_REQUEST)
            market.false_shares_remaining -= requested_shares

        market.save()

        # Create or update the MarketPosition
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
            "updated_balance": str(user_account.balance),  # ✅ Make sure balance is included
        }, status=status.HTTP_200_OK)


class UserAccountDetailView(APIView):
    def get(self, request, wallet_address):
        user = get_object_or_404(UserAccount, wallet_address=wallet_address)
        serializer = UserAccountSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MyPositionsView(APIView):
    def get(self, request, wallet_address):
        user = get_object_or_404(UserAccount, wallet_address=wallet_address)
        positions = MarketPosition.objects.filter(user=user).select_related("market", "market__claim")

        data = []
        for position in positions:
            market = position.market
            claim = market.claim
            data.append({
                "claim_id": claim.id,
                "claim_text": claim.text,
                "claim_slug": claim.slug,
                "side": position.side,
                "shares": str(position.shares),
                "cost_basis": str(position.cost_basis),
                "share_percentage": "TODO",  # We will calculate this later
                "yield": "0.00",  # Placeholder for future implementation
            })

        return Response(data, status=status.HTTP_200_OK)

from .ai_module import extract_narrative_claims  # Import your new function

class NarrativeExtractionView(APIView):
    def post(self, request, *args, **kwargs):
        text = request.data.get("text", "")
        if not text:
            return Response({"error": "Text is required."}, status=status.HTTP_400_BAD_REQUEST)

        narrative_claims = extract_narrative_claims(text)

        if narrative_claims is None:
            return Response({"error": "Failed to extract narrative claims."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"narrative_claims": narrative_claims}, status=status.HTTP_200_OK)
