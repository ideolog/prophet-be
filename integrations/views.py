# integrations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from integrations.core.integration_registry import INTEGRATION_REGISTRY
from integrations.run_integration import run_integration_for_source
from narratives.models import Source


class IntegrationRunView(APIView):
    def post(self, request, source_slug, page=1):
        try:
            source = Source.objects.filter(slug=source_slug).first()
            if not source:
                source = Source.objects.filter(id=source_slug).first()
            if not source:
                return Response({"error": f"Source '{source_slug}' not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Invalid source slug or ID format."}, status=status.HTTP_400_BAD_REQUEST)

        integration_name = "youtube" if source.platform == "youtube" else source.slug
        if integration_name not in INTEGRATION_REGISTRY:
            return Response(
                {"error": f"No integration registered for slug '{integration_name}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_payload = request.data or {}
        limit = request_payload.get("limit", 10)

        try:
            imported_count, imported_ids = run_integration_for_source(
                source, limit=limit, page=page, mark_all_not_new=True
            )
        except Exception as e:
            return Response(
                {"error": "Integration failed.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"imported_count": imported_count, "imported_rawtext_ids": imported_ids},
            status=status.HTTP_200_OK,
        )