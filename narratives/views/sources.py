from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from ..models import RawText
from ..serializers import RawTextSerializer
from ..utils.text import generate_fingerprint
from ..serializers.request_bodies import RawTextDuplicateCheckRequestSerializer

class RawTextListView(generics.ListAPIView):
    queryset = RawText.objects.all().order_by('-id')
    serializer_class = RawTextSerializer

class RawTextDetailView(generics.RetrieveAPIView):
    queryset = RawText.objects.all()
    serializer_class = RawTextSerializer
    lookup_field = 'id'

class RawTextHashDuplicateCheck(APIView):

    @swagger_auto_schema(
        request_body=RawTextDuplicateCheckRequestSerializer,
        responses={200: "Duplicate check result"}
    )
    def post(self, request):
        content = request.data.get("content", "")
        if not content:
            return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

        fingerprint = generate_fingerprint(content)
        duplicate_exists = RawText.objects.filter(content_fingerprint=fingerprint).exists()

        return Response({"duplicate": duplicate_exists}, status=status.HTTP_200_OK)

class RawTextCreateView(APIView):

    @swagger_auto_schema(
        request_body=RawTextSerializer,
        responses={201: RawTextSerializer()}
    )
    def post(self, request):
        serializer = RawTextSerializer(data=request.data)
        if serializer.is_valid():
            content = serializer.validated_data.get("content")
            fingerprint = generate_fingerprint(content)

            existing = RawText.objects.filter(content_fingerprint=fingerprint).first()
            if existing:
                return Response(RawTextSerializer(existing).data, status=status.HTTP_200_OK)

            rawtext = serializer.save(content_fingerprint=fingerprint)
            return Response(RawTextSerializer(rawtext).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
