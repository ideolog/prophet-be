# narratives/utils/categorize.py
"""Run Find Topics (keyword-based categorization) for a RawText. Used by RawTextFindTopicsView and after import."""

from django.utils import timezone

from narratives.models import Topic, PendingTopic, RawText
from narratives.models.categories import AppConfiguration
from narratives.models.analytical import TopicAnalyticalCategory
from narratives.utils.ai_module import suggest_topics_for_text
from narratives.utils.context_expand import expand_weak_keywords_for_topics_data
from narratives.utils.local_ai import analyze_swot_trigger


def _looks_like_price_ticker(paragraph: str) -> bool:
    """True if paragraph looks like a price/summary line (e.g. 'The X token is up 7% in the past 24 hours')."""
    if not paragraph or len(paragraph) > 350:
        return False
    lower = paragraph.lower()
    if "past 24 hours" in lower or "past 7 days" in lower:
        return True
    if "trading at" in lower and ("million" in lower or "billion" in lower or "market cap" in lower):
        return True
    if "is up " in lower and "%" in lower:
        return True
    return False


def run_find_topics_for_rawtext(rawtext: RawText, reset: bool = False):
    """
    Same logic as "Find topics" button: match keywords/weak keywords, create PendingTopics (auto-approved).
    Returns (suggestions_count, created_count).
    """
    if reset:
        PendingTopic.objects.filter(rawtext=rawtext).delete()

    current_version = AppConfiguration.get_version("categorization_version")

    topics = Topic.objects.filter(is_placeholder=False)
    topics_data = []
    for t in topics:
        weak_expanded = expand_weak_keywords_for_topics_data(t.weak_keywords or [])
        topics_data.append({
            "id": t.id,
            "name": t.name,
            "alternative_name": t.alternative_name,
            "keywords": t.keywords,
            "weak_keywords": weak_expanded,
        })

    title = (rawtext.title or "").strip()
    subtitle = (rawtext.subtitle or "").strip()
    content = (rawtext.content or "").strip()
    sep = "\n\n"
    zones = []  # (start, end, zone_name, weight)
    pos = 0

    parts = []
    if title:
        parts.append(title)
        zones.append((pos, pos + len(title), "title", 1))
        pos += len(title) + len(sep)
    if subtitle:
        parts.append(subtitle)
        zones.append((pos, pos + len(subtitle), "subtitle", 1))
        pos += len(subtitle) + len(sep)
    is_direct = getattr(rawtext.source, "platform", None) == "direct"
    if content:
        if is_direct:
            paras = [p.strip() for p in content.split(sep) if p.strip()] if sep in content else ([content.strip()] if content.strip() else [])
            if not paras:
                paras = [content.strip()] if content.strip() else []
            first_para = paras[0] if paras else ""
            rest_paras = paras[1:]
            if first_para and rest_paras and _looks_like_price_ticker(first_para):
                first_para, rest_paras = rest_paras[0], [paras[0]] + rest_paras[1:]
            rest_content = sep.join(rest_paras) if rest_paras else ""
            if first_para:
                parts.append(first_para)
                zones.append((pos, pos + len(first_para), "first_paragraph", 5))
                pos += len(first_para) + len(sep)
            if rest_content:
                parts.append(rest_content)
                zones.append((pos, pos + len(rest_content), "content", 1))
        else:
            parts.append(content)
            zones.append((pos, pos + len(content), "content", 1))
    text_to_search = sep.join(parts)
    if not text_to_search:
        text_to_search = rawtext.content or ""
        zones = []

    suggestions = suggest_topics_for_text(text_to_search, topics_data, zones=zones)
    created_count = 0

    for sug in suggestions:
        topic_id = sug.get("topic_id")
        context = sug.get("context")
        matched_keyword = sug.get("matched_keyword")
        is_weak = sug.get("is_weak", False)

        if not topic_id or not context:
            continue
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            continue

        if PendingTopic.objects.filter(rawtext=rawtext, topic=topic, context=context).exists():
            continue

        swot_analysis = {}
        if TopicAnalyticalCategory.objects.filter(
            topic=topic,
            analytical_category__framework__slug="swot",
            analytical_category__slug="threat",
        ).exists():
            try:
                author_name = getattr(rawtext.source, "name", None) or "the author"
                swot_result = analyze_swot_trigger(topic.name, context, author_name)
                if isinstance(swot_result, dict):
                    swot_analysis = {
                        k: swot_result[k]
                        for k in ("pestel_category", "impact_strength", "stance", "summary")
                        if k in swot_result
                    }
            except Exception as swot_err:
                pass  # skip SWOT on error

        PendingTopic.objects.create(
            rawtext=rawtext,
            topic=topic,
            context=context,
            status="approved",
            matched_keyword=matched_keyword,
            is_weak=is_weak,
            found_context_words=sug.get("found_context_words", []),
            found_in=sug.get("found_in"),
            weight=sug.get("weight", 1),
            swot_analysis=swot_analysis,
        )
        created_count += 1

    rawtext.categorization_version = current_version
    rawtext.last_categorized_at = timezone.now()
    rawtext.save(update_fields=["categorization_version", "last_categorized_at"])

    return len(suggestions), created_count
