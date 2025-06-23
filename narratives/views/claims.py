from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from narratives.utils.ai_module import extract_narrative_claims
from narratives.utils.text import generate_fingerprint
from ..models import Claim, VerificationStatus
from ..serializers import ClaimSerializer
from ..serializers.request_bodies import (
    ClaimCreateRequestSerializer, GenerateClaimsRequestSerializer
)
import logging

logger = logging.getLogger(__name__)

class ClaimDetailView(APIView):
    def get(self, request, claim_id):
        claim = get_object_or_404(Claim, id=claim_id)
        serializer = ClaimSerializer(claim)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ClaimListCreateView(APIView):

    @swagger_auto_schema(request_body=ClaimCreateRequestSerializer, responses={201: ClaimSerializer()})
    def post(self, request):
        try:
            pending_ai_status = VerificationStatus.objects.get(name='pending_ai_review')
        except VerificationStatus.DoesNotExist:
            logger.error("Verification statuses missing.")
            return Response({"error": "Verification statuses missing."}, status=500)

        submitter = request.data.get("submitter") or "UNKNOWN"
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Text is required."}, status=400)

        fingerprint = generate_fingerprint(text)
        existing_claim = Claim.objects.filter(content_fingerprint=fingerprint).first()
        if existing_claim:
            serializer = ClaimSerializer(existing_claim)
            return Response(serializer.data, status=status.HTTP_200_OK)

        claim = Claim.objects.create(
            text=text,
            verification_status=pending_ai_status,
            submitter=submitter,
            content_fingerprint=fingerprint
        )
        serializer = ClaimSerializer(claim)
        return Response(serializer.data, status=201)

    def get(self, request):
        parent_claim_id = request.GET.get("parent_claim")
        if parent_claim_id:
            claims = Claim.objects.filter(parent_claim=parent_claim_id).order_by('-created_at')
        else:
            claims = Claim.objects.all().order_by('-created_at')
        serializer = ClaimSerializer(claims, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GenerateClaimsFromTextView(APIView):

    @swagger_auto_schema(request_body=GenerateClaimsRequestSerializer, responses={201: ClaimSerializer(many=True)})
    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Text is required."}, status=400)

        narrative_claims, provider, model = extract_narrative_claims(text)
        if narrative_claims is None:
            return Response({"error": "AI extraction failed."}, status=500)

        try:
            ai_verified_status = VerificationStatus.objects.get(name='ai_reviewed')
        except VerificationStatus.DoesNotExist:
            return Response({"error": "AI verification status missing."}, status=500)

        saved_claims = []

        for claim_text in narrative_claims:
            cleaned_text = claim_text.strip()
            if not cleaned_text:
                continue

            fingerprint = generate_fingerprint(cleaned_text)
            existing_claim = Claim.objects.filter(content_fingerprint=fingerprint).first()

            if existing_claim:
                saved_claims.append(existing_claim)
            else:
                claim = Claim.objects.create(
                    text=cleaned_text,
                    verification_status=ai_verified_status,
                    submitter=provider,
                    ai_model=model,
                    generated_by_ai=True,
                    content_fingerprint=fingerprint,
                    status_description="Extracted by AI"
                )
                saved_claims.append(claim)

        serializer = ClaimSerializer(saved_claims, many=True)
        return Response({"narrative_claims": serializer.data}, status=201)
