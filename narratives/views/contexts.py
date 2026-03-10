# narratives/views/contexts.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from narratives.models import ContextSet
from narratives.serializers.contexts import ContextSetSerializer


class ContextSetListView(APIView):
    """GET list, POST create."""
    def get(self, request):
        qs = ContextSet.objects.all().order_by("slug")
        serializer = ContextSetSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ContextSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ContextSetDetailView(APIView):
    """GET, PUT, PATCH, DELETE by slug or id."""
    def get_object(self, pk_or_slug):
        from django.shortcuts import get_object_or_404
        obj = ContextSet.objects.filter(slug=pk_or_slug).first()
        if obj:
            return obj
        return get_object_or_404(ContextSet, pk=pk_or_slug)

    def get(self, request, pk_or_slug):
        obj = self.get_object(pk_or_slug)
        return Response(ContextSetSerializer(obj).data)

    def put(self, request, pk_or_slug):
        obj = self.get_object(pk_or_slug)
        serializer = ContextSetSerializer(obj, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk_or_slug):
        obj = self.get_object(pk_or_slug)
        serializer = ContextSetSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk_or_slug):
        obj = self.get_object(pk_or_slug)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
