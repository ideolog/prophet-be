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
# PUBLIC API (USED BY VIEWS)
# -------------------------

def suggest_topics_for_text(text: str, topics_data: list):
    """
    Suggests topics for a given text using FlashText for high performance.
    Level 1: FlashText (substring match) - always runs.
    Level 2: spaCy POS filter - only when pos_filter is set on a keyword.
    Level 3: AI re-verification - future.
    """
    from flashtext import KeywordProcessor
    import re

    keyword_processor = KeywordProcessor(case_sensitive=False)
    
    # Map topic_id to its weak keyword rules for context checking
    weak_rules = {}

    # Value: (topic_id, original_kw, is_weak, pos_filter)
    # pos_filter: None or ["NOUN", "PROPN"] - only accept if token has this POS
    keyword_map = {}

    for t in topics_data:
        topic_id = str(t['id'])
        
        weak_kws = [wk['keyword'].lower().strip() for wk in t.get('weak_keywords', []) if isinstance(wk, dict)]
        
        def add_to_map(kw_text, topic_info):
            kw_lower = kw_text.lower().strip()
            if not kw_lower: return
            if kw_lower not in keyword_map:
                keyword_map[kw_lower] = []
                keyword_processor.add_keyword(kw_lower)
            if topic_info not in keyword_map[kw_lower]:
                keyword_map[kw_lower].append(topic_info)

        # Topic name - no pos_filter for now
        name = t['name']
        if name.lower().strip() not in weak_kws:
            add_to_map(name, (topic_id, name, False, None))
        
        alt_name = t.get('alternative_name')
        if alt_name and alt_name.lower().strip() not in weak_kws:
            add_to_map(alt_name, (topic_id, alt_name, False, None))
        
        # Strong keywords - support both string and {keyword, pos_filter}
        for kw in t.get('keywords', []):
            if isinstance(kw, dict):
                kw_text = kw.get('keyword', '').strip()
                pos_filter = kw.get('pos_filter') or None
            else:
                kw_text = str(kw).strip()
                pos_filter = None
            if kw_text:
                add_to_map(kw_text, (topic_id, kw_text, False, pos_filter))
        
        # Weak keywords
        for wkw_obj in t.get('weak_keywords', []):
            if isinstance(wkw_obj, dict) and wkw_obj.get('keyword'):
                kw = wkw_obj['keyword'].strip()
                pos_filter = wkw_obj.get('pos_filter') or None
                add_to_map(kw, (topic_id, kw, True, pos_filter))
                
                if topic_id not in weak_rules:
                    weak_rules[topic_id] = {}
                req_ctx = [c.lower() for c in wkw_obj.get('required_context', [])]
                requires_context = wkw_obj.get('requires_context')
                if requires_context is None:
                    requires_context = len(req_ctx) > 0  # backward compat
                weak_rules[topic_id][kw.lower()] = {
                    "required_context": req_ctx,
                    "requires_context": requires_context,
                    "distance": wkw_obj.get('distance', 10),
                    "direction": wkw_obj.get('direction', 'both'),
                    "pos_filter": pos_filter,
                }

    # Extract keywords with their positions
    keywords_found = keyword_processor.extract_keywords(text, span_info=True)
    
    if not keywords_found:
        return []

    suggestions = []
    
    # Split text into sentences for better context extraction
    sentences = []
    for m in re.finditer(r'[^.!?]+[.!?]?', text):
        sentences.append({
            'text': m.group(),
            'start': m.start(),
            'end': m.end()
        })

    for matched_kw_lower, start, end in keywords_found:
        # Get all topics associated with this keyword
        topic_infos = keyword_map.get(matched_kw_lower, [])
        
        for topic_info in topic_infos:
            topic_id_str, original_kw, is_weak, pos_filter = (
                topic_info[0], topic_info[1], topic_info[2],
                topic_info[3] if len(topic_info) > 3 else None
            )
            topic_id = int(topic_id_str)
            found_context_words = []
                
            # Find the sentence containing this span
            context = ""
            context_start = 0
            context_for_pos = ""  # Raw substring for POS check (no "..." prefix)
            for s in sentences:
                if s['start'] <= start and s['end'] >= end:
                    context = s['text'].strip()
                    context_for_pos = s['text']
                    context_start = s['start']
                    break
            
            if not context:
                c_start = max(0, start - 100)
                c_end = min(len(text), end + 150)
                context_for_pos = text[c_start:c_end]
                context = context_for_pos.replace('\n', ' ').strip()
                context_start = c_start
                if c_start > 0:
                    context = "..." + context
                if c_end < len(text):
                    context = context + "..."

            # POS filter (Level 2): only when pos_filter is set - call spaCy on raw text
            if pos_filter and context_for_pos:
                match_start_in_context = start - context_start
                if not _check_pos_filter(context_for_pos, match_start_in_context, pos_filter):
                    continue

            # If it's a weak keyword, look for required context words (only when requires_context is True)
            if is_weak and topic_id_str in weak_rules:
                rules = weak_rules[topic_id_str].get(original_kw.lower())
                if rules:
                    requires_context = rules.get("requires_context", False)
                    req_context = rules.get("required_context", [])
                    if requires_context and req_context:
                        direction = rules.get("direction", "both")
                        distance = rules.get("distance", 10)
                        match_start_in_ctx = start - context_start
                        match_end_in_ctx = end - context_start
                        # Limit search area by distance (chars)
                        if direction == "left":
                            search_text = context_for_pos[max(0, match_start_in_ctx - distance):match_start_in_ctx]
                        elif direction == "right":
                            search_text = context_for_pos[match_end_in_ctx:min(len(context_for_pos), match_end_in_ctx + distance)]
                        else:
                            search_text = context_for_pos
                        # Look for context words in the relevant snippet
                        found_any_context = False
                        for word in req_context:
                            if word and word.lower() in search_text.lower():
                                found_any_context = True
                                for m in re.finditer(re.escape(word), search_text, re.IGNORECASE):
                                    found_context_words.append(m.group())
                        if not found_any_context:
                            continue

            suggestions.append({
                "topic_id": topic_id,
                "matched_keyword": original_kw,
                "context": context[:500],
                "is_weak": is_weak,
                "found_context_words": list(set(found_context_words)) # Unique words
            })

    return suggestions
