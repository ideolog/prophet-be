"""
Forbidden topic name patterns: names matching these are rejected on create/update.
Used to block auto-created topics like "Cointelegraph by Author Name" (source bylines, not concepts).
Uses FlashText to detect forbidden phrases; only rejects when match is at the start of the name.
"""
from flashtext import KeywordProcessor

# Phrases that must not start a topic name (case-insensitive). One canonical form per rule.
FORBIDDEN_TOPIC_NAME_PREFIXES = [
    "Cointelegraph by",
]

_censor_processor = None


def _get_censor_processor():
    global _censor_processor
    if _censor_processor is None:
        _censor_processor = KeywordProcessor(case_sensitive=False)
        for p in FORBIDDEN_TOPIC_NAME_PREFIXES:
            _censor_processor.add_keyword(p.strip())
    return _censor_processor


def is_forbidden_topic_name(name: str) -> bool:
    """True if the topic name should be rejected (e.g. starts with 'Cointelegraph by')."""
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if not name:
        return False
    proc = _get_censor_processor()
    found = proc.extract_keywords(name, span_info=True)
    # Reject only if any forbidden phrase appears at the start of the name (position 0)
    for _kw, start, _end in found:
        if start == 0:
            return True
    return False
