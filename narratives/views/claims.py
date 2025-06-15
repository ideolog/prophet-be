from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from ..ai_module import generate_ai_claims, extract_narrative_claims
from ..models import Claim, VerificationStatus
from ..serializers import ClaimSerializer
import logging
import time

logger = logging.getLogger(__name__)


class ClaimDetailView(APIView):
    def get(self, request, claim_id):
        claim = get_object_or_404(Claim, id=claim_id)
        serializer = ClaimSerializer(claim)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClaimListCreateView(APIView):
    def get(self, request):
        parent_claim_id = request.GET.get("parent_claim")

        if parent_claim_id:
            claims = Claim.objects.filter(parent_claim=parent_claim_id).order_by('-created_at')
        else:
            claims = Claim.objects.all().order_by('-created_at')

        serializer = ClaimSerializer(claims, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        time.sleep(1)

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

        ZERO_ADDRESS = "11111111111111111111111111111111"
        wallet_address = request.data.get("author")
        data = request.data.copy()
        data["author"] = wallet_address if wallet_address else ZERO_ADDRESS
        data['verification_status'] = pending_ai_status.id

        serializer = ClaimSerializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                try:
                    existing_claim = Claim.objects.filter(text=data['text']).first()
                    if existing_claim:
                        duplicate_claim = serializer.save(
                            verification_status=rejected_status,
                            status_description="Duplicate claim detected."
                        )
                        return Response(
                            ClaimSerializer(duplicate_claim).data,
                            status=status.HTTP_201_CREATED
                        )

                    claim = serializer.save()
                    generate_ai_claims(claim, ai_verified_status)

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


class GenerateClaimsFromTextView(APIView):
    def post(self, request, *args, **kwargs):
        text = request.data.get("text", "")
        if not text:
            return Response({"error": "Text is required."}, status=status.HTTP_400_BAD_REQUEST)

        narrative_claims = extract_narrative_claims(text)

        if narrative_claims is None:
            return Response({"error": "Failed to extract narrative claims."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"narrative_claims": narrative_claims}, status=status.HTTP_200_OK)
