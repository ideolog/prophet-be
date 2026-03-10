# integrations/run_integration.py
"""Run integration for a source and persist RawTexts. Used by IntegrationRunView and gentle_fetcher."""

from integrations.core.integration_registry import INTEGRATION_REGISTRY
from narratives.models import Source, RawText, Genre, Topic, TopicType
from narratives.utils.text import generate_fingerprint
from narratives.utils.categorize import run_find_topics_for_rawtext


def run_integration_for_source(source: Source, limit: int = 1, page: int = 1, mark_all_not_new: bool = False):
    """
    Fetch content from the integration for `source`, normalize to rawtexts, create/update RawText.
    Returns (imported_count, imported_rawtext_ids).
    If mark_all_not_new is True, all RawTexts are marked is_new=False before processing (legacy view behavior).
    """
    integration_name = "youtube" if source.platform == "youtube" else source.slug
    if integration_name not in INTEGRATION_REGISTRY:
        raise ValueError(f"No integration registered for '{integration_name}'")

    integration = INTEGRATION_REGISTRY[integration_name]
    source_config = {
        "timezone": getattr(source, "timezone", "UTC"),
        "page": page,
        "limit": limit,
    }

    raw_data = integration.fetch_content(source=source, source_config=source_config)
    rawtexts = integration.normalize_to_rawtext(raw_data, source=source, source_config=source_config)

    if mark_all_not_new:
        RawText.objects.all().update(is_new=False, is_updated=False)

    imported = []
    for raw in rawtexts:
        content = (raw.get("content") or "").strip()
        source_url = raw.get("source_url")
        if not content:
            continue

        fingerprint = generate_fingerprint(content)

        existing_by_url = None
        if source_url:
            existing_by_url = RawText.objects.filter(source_url=source_url).first()

        if existing_by_url:
            if existing_by_url.content_fingerprint != fingerprint:
                existing_by_url.content = content
                existing_by_url.content_fingerprint = fingerprint
                new_title = (raw.get("title") or "").strip()
                if new_title:
                    existing_by_url.title = new_title
                new_subtitle = (raw.get("subtitle") or "").strip()
                if new_subtitle:
                    existing_by_url.subtitle = new_subtitle
                existing_by_url.is_updated = True
                existing_by_url.is_new = False
                existing_by_url.save()
                imported.append(existing_by_url.id)
            continue

        existing_rawtext = RawText.objects.filter(content_fingerprint=fingerprint).first()
        if existing_rawtext:
            new_title = (raw.get("title") or "").strip()
            if new_title and (not existing_rawtext.title or existing_rawtext.title.startswith("YouTube video")):
                existing_rawtext.title = new_title
                existing_rawtext.is_updated = True
                existing_rawtext.is_new = False
                existing_rawtext.save()
                imported.append(existing_rawtext.id)
            continue

        genre_name = (raw.get("genre") or "speech").strip().lower()
        genre, _ = Genre.objects.get_or_create(name=genre_name)

        author_name = (raw.get("author") or "").strip()
        author = None
        if author_name:
            author, _ = Topic.objects.get_or_create(name=author_name)
            person_type = TopicType.objects.filter(name="Person").first()
            if person_type:
                author.topic_type = person_type
                author.save()

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
        # Auto-categorize: same as "Find topics" (keywords + weak keywords → PendingTopics)
        try:
            run_find_topics_for_rawtext(rawtext, reset=False)
        except Exception:
            pass  # do not fail import if categorization fails

    return len(imported), imported
