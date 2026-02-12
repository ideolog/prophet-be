from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from integrations.core.integration_registry import INTEGRATION_REGISTRY
from narratives.models.sources import Source, RawText, Genre
from narratives.utils.text import generate_fingerprint

class IntegrationRunView(APIView):

    def post(self, request, source_slug, page=1):

        try:
            source = Source.objects.get(slug=source_slug)
        except Source.DoesNotExist:
            return Response({"error": "Invalid source slug."}, status=status.HTTP_400_BAD_REQUEST)

        integration_name = source.slug  # use slug as integration key

        if integration_name not in INTEGRATION_REGISTRY:
            return Response({"error": f"No integration registered for slug '{integration_name}'."}, status=status.HTTP_400_BAD_REQUEST)

        integration = INTEGRATION_REGISTRY[integration_name]

        # Prepare source config
        source_config = {
            "timezone": source.timezone,
            "page": page,
            **(request.data or {}),
        }

        raw_data = integration.fetch_content(source_config=source_config)
        rawtexts = integration.normalize_to_rawtext(raw_data, source_config=source_config)

        imported = []
        for raw in rawtexts:
            content = raw.get("content")
            if not content:
                continue

            fingerprint = generate_fingerprint(content)
            existing = RawText.objects.filter(content_fingerprint=fingerprint).first()
            if existing:
                continue

            rawtext = RawText.objects.create(
                title=raw.get("title"),
                subtitle=raw.get("subtitle"),
                author=raw.get("author"),
                content=content,
                published_at=raw.get("published_at"),
                source_url=raw.get("source_url"),   # ✅ <-- NEW FIELD STORED
                source=source,
                genre=Genre.objects.get_or_create(name="speech")[0],
                content_fingerprint=fingerprint
            )
            imported.append(rawtext.id)

        return Response({
            "imported_count": len(imported),
            "imported_rawtext_ids": imported
        }, status=status.HTTP_200_OK)
