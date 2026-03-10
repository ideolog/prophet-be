# narratives/utils/context_expand.py
"""Expand [SLUG] references in required_context to the ContextSet's words."""

import re
from narratives.models import ContextSet


def expand_required_context(required_context: list, context_sets_by_slug: dict = None) -> list:
    """
    required_context: list of strings, e.g. ["crypto", "[CRYPTO_WEAK_CONTEXT]", "token"].
    Returns flat list with [SLUG] replaced by that ContextSet's words.
    """
    if not required_context:
        return []
    if context_sets_by_slug is None:
        context_sets_by_slug = {cs.slug: (cs.words or []) for cs in ContextSet.objects.all()}
    result = []
    for item in required_context:
        s = (item or "").strip()
        if not s:
            continue
        m = re.match(r"^\[([A-Za-z0-9_]+)\]$", s)
        if m:
            slug = m.group(1)
            words = context_sets_by_slug.get(slug, [])
            result.extend([w for w in words if w])
        else:
            result.append(s)
    return result


def expand_weak_keywords_for_topics_data(weak_keywords: list, context_sets_by_slug: dict = None) -> list:
    """In-place style: return new list of weak_keyword dicts with required_context expanded."""
    if not weak_keywords:
        return []
    if context_sets_by_slug is None:
        context_sets_by_slug = {cs.slug: (cs.words or []) for cs in ContextSet.objects.all()}
    out = []
    for wkw in weak_keywords:
        if not isinstance(wkw, dict):
            out.append(wkw)
            continue
        req = wkw.get("required_context") or []
        expanded = expand_required_context(req, context_sets_by_slug)
        out.append({**wkw, "required_context": expanded})
    return out
