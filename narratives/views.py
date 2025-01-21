from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from .models import Narrative, Claim, VerificationStatus
from .serializers import NarrativeSerializer, ClaimSerializer
from .linguistic_module import check_claim_validity
import time

class ClaimDetailView(APIView):
    def get(self, request, slug):
        claim = get_object_or_404(Claim, slug=slug)
        serializer = ClaimSerializer(claim)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ClaimListCreateView(APIView):
    def get(self, request):
        claims = Claim.objects.all().order_by('-created_at')
        serializer = ClaimSerializer(claims, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        time.sleep(1)  # Simulate delay for testing purposes

        # Fetch required statuses
        try:
            default_status = VerificationStatus.objects.get(name='unverified')
            pending_ai_status = VerificationStatus.objects.get(name='pending_ai_review')
            rejected_status = VerificationStatus.objects.get(name='rejected')
        except VerificationStatus.DoesNotExist:
            return Response(
                {"error": "One or more required verification statuses are missing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Set default status for the new claim
        data = request.data.copy()
        data['verification_status'] = default_status.id

        serializer = ClaimSerializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                claim = serializer.save()  # Save the claim with 'unverified' status

                try:
                    # Perform linguistic validation
                    check_claim_validity(claim)
                    claim.verification_status = pending_ai_status
                    claim.status_description = "Claim passed linguistic checks and is ready for AI review."
                except ValidationError as e:
                    claim.verification_status = rejected_status
                    claim.status_description = e.messages[0] if e.messages else "Unknown validation error."
                finally:
                    claim.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class NarrativeListView(generics.ListAPIView):
    queryset = Narrative.objects.all()
    serializer_class = NarrativeSerializer