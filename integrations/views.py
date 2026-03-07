# integrations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from integrations.core.integration_registry import INTEGRATION_REGISTRY
from narratives.models import Source, RawText, Genre, Topic
from narratives.utils.text import generate_fingerprint


class IntegrationRunView(APIView):
    def post(self, request, source_slug, page=1):
        try:
            source = Source.objects.get(slug=source_slug)
        except Source.DoesNotExist:
            # Try to find by ID if slug doesn't match
            try:
                source = Source.objects.get(id=source_slug)
            except (Source.DoesNotExist, ValueError):
                return Response({"error": "Invalid source slug or ID."}, status=status.HTTP_400_BAD_REQUEST)

        integration_name = "youtube" if source.platform == "youtube" else source.slug
        if integration_name not in INTEGRATION_REGISTRY:
            return Response(
                {"error": f"No integration registered for slug '{integration_name}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        integration = INTEGRATION_REGISTRY[integration_name]

        # Allow both "page" and "limit" patterns (RSS integrations typically use "limit")
        request_payload = request.data or {}
        limit = request_payload.get("limit", 10)

        source_config = {
            "timezone": source.timezone,
            "page": page,
            "limit": limit,
            **request_payload,
        }

        try:
            raw_data = integration.fetch_content(source=source, source_config=source_config)
            rawtexts = integration.normalize_to_rawtext(raw_data, source=source, source_config=source_config)
        except Exception as e:
            return Response(
                {"error": "Integration failed.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Mark all existing as not new/updated across all sources
        RawText.objects.all().update(is_new=False, is_updated=False)

        imported = []
        for raw in rawtexts:
            content = (raw.get("content") or "").strip()
            if not content:
                continue

            fingerprint = generate_fingerprint(content)
            existing_rawtext = RawText.objects.filter(content_fingerprint=fingerprint).first()
            
            if existing_rawtext:
                # Check if we can update something (e.g. title if it was generic before)
                new_title = (raw.get("title") or "").strip()
                if new_title and (not existing_rawtext.title or existing_rawtext.title.startswith("YouTube video")):
                    existing_rawtext.title = new_title
                    existing_rawtext.is_updated = True
                    existing_rawtext.save()
                    imported.append(existing_rawtext.id) # Add to imported to trigger redirect/badge
                continue

            genre_name = (raw.get("genre") or "speech").strip().lower()
            genre, _ = Genre.objects.get_or_create(name=genre_name)

            author_name = (raw.get("author") or "").strip()
            author = None
            if author_name:
                author, _ = Topic.objects.get_or_create(name=author_name)
                # Ensure it has Person parent
                person_root, _ = Topic.objects.get_or_create(name="Person")
                author.parents.add(person_root)

            rawtext = RawText.objects.create(
                title=(raw.get("title") or "").strip() or None,
                subtitle=(raw.get("subtitle") or "").strip() or None,
                author=author,
                content=content,
                published_at=raw.get("published_at"),
                source_url=raw.get("source_url"),
                source=source,
                genre=genre,
                content_fingerprint=fingerprint,
                is_new=True,
                is_updated=False,
            )
            imported.append(rawtext.id)

        return Response(
            {"imported_count": len(imported), "imported_rawtext_ids": imported},
            status=status.HTTP_200_OK,
        )