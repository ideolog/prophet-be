import os
import json
import re
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------
# POS FILTER (spaCy) - Level 2, called only when pos_filter is set
# -------------------------

_nlp = None

def _get_nlp():
    """Lazy-load spaCy model. Only loaded when pos_filter is used."""
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def _check_pos_filter(context: str, match_start_in_context: int, pos_filter: list) -> bool:
    """
    Check if the token at match_start_in_context has one of the allowed POS tags.
    pos_filter: e.g. ["NOUN", "PROPN"] - spaCy universal POS tags.
    Returns True if the matched token's POS is in pos_filter, False otherwise.
    """
    if not pos_filter or not context:
        return True
    pos_filter_set = {p.upper().strip() for p in pos_filter if p}
    if not pos_filter_set:
        return True
    try:
        nlp = _get_nlp()
        doc = nlp(context)
        for token in doc:
            # token.idx is start char offset of token in the doc
            if token.idx <= match_start_in_context < token.idx + len(token.text):
                return token.pos_ in pos_filter_set
        return False
    except Exception:
        return False

# -------------------------
# ENTITY EXTRACTION (spaCy) - Level 1, called for hybrid suggestions
# -------------------------

def extract_entities_with_spacy(text: str, labels=["PERSON", "ORG"]):
    """
    Extracts named entities from text using spaCy.
    Maps labels to actual TopicType from DB (Person, Organization) so suggested_type_id is always valid.
    """
    if not text:
        return []
    
    try:
        from narratives.models import TopicType
        # Resolve Person / Organization from DB (no hardcoded IDs)
        label_to_type_name = {"PERSON": "Person", "ORG": "Organization"}
        label_map = {}
        for spacy_label, type_name in label_to_type_name.items():
            tt = TopicType.objects.filter(name=type_name).first()
            if tt:
                label_map[spacy_label] = {"id": tt.id, "name": tt.name}
            else:
                label_map[spacy_label] = None  # type not in DB, skip suggesting type for this label

        nlp = _get_nlp()
        doc = nlp(text)
        
        entities = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ in labels:
                clean_text = ent.text.strip()
                
                # Filter out obvious false positives for PERSON and ORG
                # 1. All caps short words (likely tickers like BTC, ETH) - these are NOT people or orgs
                if clean_text.isupper() and len(clean_text) <= 4:
                    continue
                
                # 2. Common crypto terms that spaCy misidentifies as PERSON/ORG
                # We don't blacklist them from the system, just prevent spaCy from 
                # incorrectly tagging them as a "Person" or "Organization".
                # These will be handled by the LLM as general concepts or Collective Actors.
                spacy_ner_noise = {
                    "whale", "whales", "bull", "bear", "bulls", "bears",
                    "moon", "pump", "dump", "gas", "fiat", "stablecoin",
                    "holders", "hodlers", "traders", "investors"
                }
                if clean_text.lower() in spacy_ner_noise:
                    continue

                # Basic cleanup and deduplication
                type_info = label_map.get(ent.label_) if ent.label_ in label_map else None
                if clean_text and len(clean_text) > 2 and clean_text.lower() not in seen:
                    entities.append({
                        "name": clean_text,
                        "label": ent.label_,
                        "suggested_type_id": type_info["id"] if type_info else None,
                        "suggested_type_name": type_info["name"] if type_info else None
                    })
                    seen.add(clean_text.lower())
        
        return entities
    except Exception as e:
        print(f"Entity extraction failed: {e}")
        return []

# -------------------------
# PUBLIC API (USED BY VIEWS)
# -------------------------

from flashtext import KeywordProcessor
from django.core.cache import cache
import hashlib

from narratives.utils.text import get_keyword_spec_from_entry

# -------------------------
# KEYWORD ENGINE CACHING
# -------------------------

def _topic_config_signature(t: dict) -> str:
    """Signature for cache: include keyword text and whole_word_only/case_sensitive."""
    parts = []
    for entry in t.get('keywords', []) + t.get('weak_keywords', []):
        kw, wo, cs = get_keyword_spec_from_entry(entry)
        if kw:
            parts.append(f"{kw}:{wo}:{cs}")
    return "|".join(parts)


def _get_keyword_processor(topics_data: list):
    """
    Returns FlashText processor (whole-word case-insensitive), keyword_map, weak_rules,
    plus case_sensitive_list and substring_list for separate passes.
    """
    config_state = []
    for t in topics_data:
        config_state.append(f"{t['id']}:{len(t.get('keywords', []))}:{len(t.get('weak_keywords', []))}:{_topic_config_signature(t)}")
    config_hash = hashlib.md5(",".join(config_state).encode()).hexdigest()
    cache_key = f"keyword_processor_{config_hash}"
    cached = cache.get(cache_key)
    if cached:
        return (
            cached['processor'], cached['keyword_map'], cached['weak_rules'],
            cached['case_sensitive_list'], cached['substring_list']
        )

    keyword_processor = KeywordProcessor(case_sensitive=False)
    keyword_map = {}
    weak_rules = {}
    case_sensitive_list = []
    substring_list = []

    for t in topics_data:
        topic_id = str(t['id'])
        # All keyword texts (strong + weak): explicit keyword overrides name/alternative_name for same text
        explicit_keyword_texts = set()
        for entry in t.get('keywords', []) + t.get('weak_keywords', []):
            kw_text, _, _ = get_keyword_spec_from_entry(entry)
            if kw_text:
                explicit_keyword_texts.add(kw_text.strip().lower())

        def add_flashtext(kw_text, topic_info):
            kw_lower = kw_text.lower().strip()
            if not kw_lower:
                return
            if kw_lower not in keyword_map:
                keyword_map[kw_lower] = []
                keyword_processor.add_keyword(kw_lower)
            if topic_info not in keyword_map[kw_lower]:
                keyword_map[kw_lower].append(topic_info)

        name = (t.get('name') or '').strip()
        if name and name.lower() not in explicit_keyword_texts:
            add_flashtext(name, (topic_id, name, False, None))
        alt_name = (t.get('alternative_name') or '').strip()
        if alt_name and alt_name.lower() not in explicit_keyword_texts:
            add_flashtext(alt_name, (topic_id, alt_name, False, None))

        for kw in t.get('keywords', []):
            kw_text, whole_word, case_sens = get_keyword_spec_from_entry(kw)
            pos_filter = kw.get('pos_filter') if isinstance(kw, dict) else None
            if not kw_text:
                continue
            if whole_word and not case_sens:
                add_flashtext(kw_text, (topic_id, kw_text, False, pos_filter))
            elif whole_word and case_sens:
                case_sensitive_list.append((topic_id, kw_text, False, pos_filter))
            else:
                substring_list.append((topic_id, kw_text, False, pos_filter))

        for wkw_obj in t.get('weak_keywords', []):
            if not isinstance(wkw_obj, dict) or not wkw_obj.get('keyword'):
                continue
            kw_text, whole_word, case_sens = get_keyword_spec_from_entry(wkw_obj)
            pos_filter = wkw_obj.get('pos_filter')
            if not kw_text:
                continue
            req_ctx = [c.lower() for c in wkw_obj.get('required_context', [])]
            requires_context = wkw_obj.get('requires_context')
            if requires_context is None:
                requires_context = len(req_ctx) > 0
            rule = {
                "required_context": req_ctx,
                "requires_context": requires_context,
                "distance": wkw_obj.get('distance', 10),
                "direction": wkw_obj.get('direction', 'both'),
                "pos_filter": pos_filter,
            }
            if topic_id not in weak_rules:
                weak_rules[topic_id] = {}
            rule_key = kw_text if case_sens else kw_text.lower()
            weak_rules[topic_id][rule_key] = rule
            if whole_word and not case_sens:
                add_flashtext(kw_text, (topic_id, kw_text, True, pos_filter))
            elif whole_word and case_sens:
                case_sensitive_list.append((topic_id, kw_text, True, pos_filter))
            else:
                substring_list.append((topic_id, kw_text, True, pos_filter))

    result = {
        'processor': keyword_processor,
        'keyword_map': keyword_map,
        'weak_rules': weak_rules,
        'case_sensitive_list': case_sensitive_list,
        'substring_list': substring_list,
    }
    cache.set(cache_key, result, 3600)
    return keyword_processor, keyword_map, weak_rules, case_sensitive_list, substring_list

def _apply_weak_rules(is_weak, topic_id_str, original_kw, start, end, context, context_start, context_for_pos, weak_rules):
    """Returns (passed, found_context_words).
    Required context words are matched case-insensitively and as substrings (may be part of other words, e.g. 'crypto' in 'cryptocurrency').
    """
    if not is_weak or topic_id_str not in weak_rules:
        return True, []
    rules = weak_rules[topic_id_str].get(original_kw) or weak_rules[topic_id_str].get(original_kw.lower())
    if not rules:
        return True, []
    requires_context = rules.get("requires_context", False)
    req_context = rules.get("required_context", [])
    if not requires_context or not req_context:
        return True, []
    direction = rules.get("direction", "both")
    distance = rules.get("distance", 10)
    match_start_in_ctx = start - context_start
    match_end_in_ctx = end - context_start
    if direction == "left":
        search_text = context_for_pos[max(0, match_start_in_ctx - distance):match_start_in_ctx]
    elif direction == "right":
        search_text = context_for_pos[match_end_in_ctx:min(len(context_for_pos), match_end_in_ctx + distance)]
    else:
        search_text = context_for_pos
    # Required context words (no quotes, no !): match case-insensitive and as substring (can be part of other words).
    found_context_words = []
    search_lower = search_text.lower()
    for word in req_context:
        if not word:
            continue
        word_lower = word.lower()
        if word_lower not in search_lower:
            continue
        # Substring match, case-insensitive (re.IGNORECASE) — e.g. "crypto" matches "cryptocurrency", "Crypto", etc.
        for m in re.finditer(re.escape(word), search_text, re.IGNORECASE):
            found_context_words.append(m.group())
    return len(found_context_words) > 0, list(set(found_context_words))


def _zone_for_position(position: int, zones: list) -> tuple:
    """Return (found_in, weight) for character position. zones: [(start, end, zone_name, weight), ...]."""
    for (z_start, z_end, zone_name, weight) in zones:
        if z_start <= position < z_end:
            return (zone_name, weight)
    return ("content", 1)


def suggest_topics_for_text(text: str, topics_data: list, zones: list = None):
    """
    Suggests topics for a given text: FlashText (whole-word case-insensitive),
    then case-sensitive whole-word pass, then substring pass.
    zones: optional list of (start, end, zone_name, weight) to set found_in and weight per suggestion.
    """
    keyword_processor, keyword_map, weak_rules, case_sensitive_list, substring_list = _get_keyword_processor(topics_data)
    zones = zones or []

    sentences = []
    for m in re.finditer(r'[^.!?]+[.!?]?', text):
        sentences.append({'text': m.group(), 'start': m.start(), 'end': m.end()})

    seen_span = set()  # (topic_id, start, end) to dedupe
    suggestions = []

    def get_context(text, sentences, start, end):
        for s in sentences:
            if s['start'] <= start and s['end'] >= end:
                return s['text'].strip(), s['text'], s['start']
        c_start = max(0, start - 100)
        c_end = min(len(text), end + 150)
        ctx_raw = text[c_start:c_end]
        ctx = ctx_raw.replace('\n', ' ').strip()
        if c_start > 0:
            ctx = "..." + ctx
        if c_end < len(text):
            ctx = ctx + "..."
        return ctx, ctx_raw, c_start

    def add_suggestion(topic_id, start, end, keyword_for_rules, matched_keyword_display, is_weak, pos_filter):
        key = (str(topic_id), start, end)
        if key in seen_span:
            return
        context, context_for_pos, context_start = get_context(text, sentences, start, end)
        if pos_filter and context_for_pos:
            match_start_in_context = start - context_start
            if not _check_pos_filter(context_for_pos, match_start_in_context, pos_filter):
                return
        passed, found_context_words = _apply_weak_rules(
            is_weak, str(topic_id), keyword_for_rules, start, end, context, context_start, context_for_pos, weak_rules
        )
        if not passed:
            return
        seen_span.add(key)
        found_in, weight = _zone_for_position(start, zones)
        suggestions.append({
            "topic_id": int(topic_id),
            "matched_keyword": matched_keyword_display,
            "context": (context or "")[:500],
            "is_weak": is_weak,
            "found_context_words": found_context_words,
            "found_in": found_in,
            "weight": weight,
        })

    # 1) FlashText pass (whole-word, case-insensitive)
    keywords_found = keyword_processor.extract_keywords(text, span_info=True)
    for matched_kw_lower, start, end in keywords_found:
        topic_infos = keyword_map.get(matched_kw_lower, [])
        for topic_info in topic_infos:
            topic_id_str, original_kw, is_weak, pos_filter = (
                topic_info[0], topic_info[1], topic_info[2],
                topic_info[3] if len(topic_info) > 3 else None
            )
            add_suggestion(int(topic_id_str), start, end, original_kw, original_kw, is_weak, pos_filter)

    # 2) Case-sensitive whole-word pass (!"WHO")
    for topic_id_str, kw_exact, is_weak, pos_filter in case_sensitive_list:
        for m in re.finditer(r'\b' + re.escape(kw_exact) + r'\b', text):
            add_suggestion(int(topic_id_str), m.start(), m.end(), kw_exact, kw_exact, is_weak, pos_filter)

    # 3) Substring pass (whole_word_only=False); rule lookup by stored keyword, display matched text
    for topic_id_str, kw, is_weak, pos_filter in substring_list:
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            matched_text = text[m.start():m.end()]
            add_suggestion(int(topic_id_str), m.start(), m.end(), kw, matched_text, is_weak, pos_filter)

    return suggestions
