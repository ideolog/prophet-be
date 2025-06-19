# views/sources.py

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from ..models import RawText
from ..serializers import RawTextSerializer
from ..utils.text import generate_fingerprint


class RawTextListView(generics.ListAPIView):
    queryset = RawText.objects.all().order_by('-id')
    serializer_class = RawTextSerializer


class RawTextDetailView(generics.RetrieveAPIView):
    queryset = RawText.objects.all()
    serializer_class = RawTextSerializer
    lookup_field = 'id'


class RawTextHashDuplicateCheck(APIView):
    def post(self, request):
        content = request.data.get("content", "")
        if not content:
            return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

        fingerprint = generate_fingerprint(content)
        duplicate_exists = RawText.objects.filter(content_fingerprint=fingerprint).exists()

        return Response({"duplicate": duplicate_exists}, status=status.HTTP_200_OK)

# views/sources.py
class RawTextCreateView(APIView):
    def post(self, request):
        serializer = RawTextSerializer(data=request.data)
        if serializer.is_valid():
            rawtext = serializer.save()
            return Response(RawTextSerializer(rawtext).data, status=201)
        return Response(serializer.errors, status=400)
