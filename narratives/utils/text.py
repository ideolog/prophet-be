import re
import unicodedata
import hashlib


def generate_fingerprint(text):
    # Normalize unicode (remove diacritics etc.)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = ''.join(c for c in text if c.isprintable() and not unicodedata.category(c).startswith('C'))

    # Lowercase
    text = text.lower()

    # Remove everything except letters and numbers
    text = re.sub(r'[^a-z0-9]', '', text)

    # Generate md5 hash
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def parse_keyword_spec(raw: str) -> dict:
    """
    Parse keyword notation: !"WHO" = whole word + case sensitive, "X" = whole word,
    print = substring. Returns dict with keyword, whole_word_only, case_sensitive.
    """
    if not isinstance(raw, str):
        raw = str(raw).strip()
    else:
        raw = raw.strip()
    if not raw:
        return {"keyword": "", "whole_word_only": False, "case_sensitive": False}
    # !"..." or !'...'
    if len(raw) >= 3 and raw[0] == "!" and raw[1] in "\"'" and raw[-1] == raw[1]:
        return {
            "keyword": raw[2:-1].strip(),
            "whole_word_only": True,
            "case_sensitive": True,
        }
    # "..." or '...'
    if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
        return {
            "keyword": raw[1:-1].strip(),
            "whole_word_only": True,
            "case_sensitive": False,
        }
    return {
        "keyword": raw,
        "whole_word_only": False,
        "case_sensitive": False,
    }


def get_keyword_spec_from_entry(entry) -> tuple:
    """
    From a stored keyword entry (string or dict), return (keyword_text, whole_word_only, case_sensitive).
    String entries like !"S" or "X" are parsed via parse_keyword_spec; plain words stay whole_word=True, case_sensitive=False.
    """
    if entry is None:
        return ("", True, False)
    if isinstance(entry, str):
        text = entry.strip()
        if not text:
            return ("", True, False)
        # Parse notation: !"S" → whole word + case sensitive, "X" → whole word, plain → whole word (legacy)
        if (len(text) >= 2 and text[0] in "\"'") or (len(text) >= 3 and text[0] == "!" and text[1] in "\"'"):
            spec = parse_keyword_spec(text)
            return (spec["keyword"], spec["whole_word_only"], spec["case_sensitive"])
        return (text, True, False)  # plain string: whole word, case insensitive
    if isinstance(entry, dict):
        kw = entry.get("keyword") or ""
        if isinstance(kw, str):
            kw = kw.strip()
        else:
            kw = str(kw).strip()
        # New format: explicit flags
        if "whole_word_only" in entry or "case_sensitive" in entry:
            return (kw, bool(entry.get("whole_word_only", True)), bool(entry.get("case_sensitive", False)))
        # Old dict format (e.g. weak_keywords with only keyword, required_context, ...)
        return (kw, True, False)
    return (str(entry).strip(), True, False)


def title_contains_keyword_as_word(title: str, keyword: str, case_sensitive: bool = False) -> bool:
    """True if title contains keyword as a whole word (avoids 'X' matching inside 'Next')."""
    if not keyword or not title:
        return False
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(r"\b" + re.escape(keyword.strip()) + r"\b", flags)
    return pattern.search(title) is not None


def topic_title_matches_keyword(topic, matched_keyword: str, title: str) -> bool:
    """
    Whether the title matches the given matched_keyword according to the topic's
    keyword spec (whole_word_only, case_sensitive). Same rules as content search.
    matched_keyword is what was found (e.g. "printing" for substring keyword "print").
    """
    if not title or not matched_keyword:
        return False
    keyword_text = matched_keyword.strip()
    whole_word_only = True
    case_sensitive = False
    for entry in (topic.keywords or []) + (topic.weak_keywords or []):
        kw, whole, case = get_keyword_spec_from_entry(entry)
        if not kw:
            continue
        if whole:
            match = (kw == keyword_text) or (not case and kw.lower() == keyword_text.lower())
        else:
            match = kw.lower() in keyword_text.lower() or keyword_text.lower() in kw.lower()
        if match:
            whole_word_only = whole
            case_sensitive = case
            break
    if whole_word_only:
        return title_contains_keyword_as_word(title, keyword_text, case_sensitive=case_sensitive)
    if case_sensitive:
        return keyword_text in title
    return keyword_text.lower() in title.lower()

