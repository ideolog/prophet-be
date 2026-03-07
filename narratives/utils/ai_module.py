import os
import json
import re
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------
# PUBLIC API (USED BY VIEWS)
# -------------------------

def suggest_topics_for_text(text: str, topics_data: list):
    """
    Suggests topics for a given text using FlashText for high performance.
    Handles both strong and weak keywords.
    """
    from flashtext import KeywordProcessor
    import re

    keyword_processor = KeywordProcessor(case_sensitive=False)
    
    # Map topic_id to its weak keyword rules for context checking
    # { topic_id: { "keyword": { "required_context": [], "distance": 10 } } }
    weak_rules = {}

    for t in topics_data:
        topic_id = str(t['id'])
        
        # Get weak keywords for this topic to check for overrides
        weak_kws = [wk['keyword'].lower().strip() for wk in t.get('weak_keywords', [])]
        
        # Add topic name as a strong keyword ONLY if it's not already defined as a weak keyword
        name = t['name']
        name_lower = name.lower().strip()
        if name_lower not in weak_kws:
            keyword_processor.add_keyword(name, (topic_id, name, False))
        
        # Add alternative name if exists, also checking for weak keyword overrides
        alt_name = t.get('alternative_name')
        if alt_name:
            alt_name_lower = alt_name.lower().strip()
            if alt_name_lower not in weak_kws:
                keyword_processor.add_keyword(alt_name, (topic_id, alt_name, False))
        
        # Add strong keywords
        for kw in t.get('keywords', []):
            if kw.strip():
                keyword_processor.add_keyword(kw.strip(), (topic_id, kw.strip(), False))
        
        # Add weak keywords
        for wkw_obj in t.get('weak_keywords', []):
            if isinstance(wkw_obj, dict) and wkw_obj.get('keyword'):
                kw = wkw_obj['keyword'].strip()
                keyword_processor.add_keyword(kw, (topic_id, kw, True))
                
                if topic_id not in weak_rules:
                    weak_rules[topic_id] = {}
                weak_rules[topic_id][kw.lower()] = {
                    "required_context": [c.lower() for c in wkw_obj.get('required_context', [])],
                    "distance": wkw_obj.get('distance', 10)
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

    for (topic_id_str, matched_kw, is_weak), start, end in keywords_found:
        topic_id = int(topic_id_str)
        found_context_words = []
            
        # Find the sentence containing this span
        context = ""
        for s in sentences:
            if s['start'] <= start and s['end'] >= end:
                context = s['text'].strip()
                break
        
        if not context:
            c_start = max(0, start - 100)
            c_end = min(len(text), end + 150)
            context = text[c_start:c_end].replace('\n', ' ').strip()
            if c_start > 0: context = "..." + context
            if c_end < len(text): context = context + "..."

        # If it's a weak keyword, look for required context words to highlight them
        if is_weak and topic_id_str in weak_rules:
            rules = weak_rules[topic_id_str].get(matched_kw.lower())
            if rules:
                req_context = rules.get("required_context", [])
                if req_context:
                    # Look for these words in the context snippet
                    for word in req_context:
                        if word and word.lower() in context.lower():
                            # Find the actual casing in the context
                            matches = re.finditer(re.escape(word), context, re.IGNORECASE)
                            for m in matches:
                                found_context_words.append(m.group())

        suggestions.append({
            "topic_id": topic_id,
            "matched_keyword": matched_kw,
            "context": context[:500],
            "is_weak": is_weak,
            "found_context_words": list(set(found_context_words)) # Unique words
        })

    return suggestions
