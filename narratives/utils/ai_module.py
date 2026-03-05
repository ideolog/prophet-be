import os
import json
import re
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------
# PROMPTS
# -------------------------

SYSTEM_PROMPT_CRYPTO = (
    "You are a Crypto Narrative Claim Extractor.\n"
    "Your task is to analyze crypto market analysis videos, podcasts, interviews and blog posts, and extract a list of NARRATIVE CLAIMS about blockchain and cryptocurrency.\n\n"
    "🎯 Your goal is to extract statements that reflect beliefs, predictions or assumptions about cryptocurrencies, blockchain technology, market dynamics, valuations, adoption, regulation and their societal impact.\n\n"
    "✅ EXTRACT claims that include:\n"
    "- 📈 Predictions about price movements or market cycles (e.g., 'Bitcoin will reach $100k soon').\n"
    "- 🔍 Assertions about network fundamentals or technological superiority (e.g., 'Ethereum’s shift to proof-of-stake makes it the most scalable chain').\n"
    "- 🤝 Claims about adoption and use cases (e.g., 'DeFi will replace traditional banking').\n"
    "- 📜 Regulatory or political statements affecting crypto (e.g., 'SEC enforcement actions are stifling innovation').\n"
    "- 🧠 Narratives about macro-economic factors influencing crypto (e.g., 'Crypto is a hedge against inflation').\n\n"
    "🚫 DO NOT EXTRACT:\n"
    "- ✅ Простые новостные сообщения и факты (e.g., 'Coinbase listed a new token today').\n"
    "- 🔄 Технические описания без мнения (e.g., 'Ethereum forked at block 12M').\n"
    "- 🙌 Общие лозунги без конкретного утверждения (e.g., 'Cryptocurrency is awesome').\n\n"
    "✍️ Guidelines:\n"
    "- Rewrite each extracted idea as a short, clear, independent sentence.\n"
    "- Avoid direct quotes; paraphrase in a neutral tone.\n"
    "- Do not join multiple ideas with 'and', 'but' or 'or'; one claim per sentence.\n"
    "- Include statements reflecting present or past beliefs; include future predictions only if they are explicit price or adoption forecasts.\n\n"
    "📦 Output format:\n"
    "Return ONLY a JSON object like: { \"narrative_claims\": [\"Claim 1.\", \"Claim 2.\", …] }\n"
    "Return ONLY the JSON — no extra text or commentary."
)

SYSTEM_PROMPT_IDEOLOGY = (
    "You are a Narrative Claim Extractor.\n"
    "Your task is to analyze political speeches, government press releases, legal statements, social media posts, "
    "and public addresses by political figures, and extract a list of NARRATIVE or IDEOLOGICAL CLAIMS.\n\n"
    "🎯 Your goal is to extract the **underlying worldview, assumptions, and value-based assertions** expressed in the text.\n"
    "These are statements that reflect beliefs about how the world works, what is right or wrong, or who is to blame or praised.\n\n"
    "✅ EXTRACT claims that include:\n"
    "- 💥 Enemy accusations (e.g., 'This war was started by Russia.')\n"
    "- ⚙️ Cause-effect logic (e.g., 'The Ukrainian revolution caused Russia to defend Russian people.')\n"
    "- 🧠 Worldview formulas (e.g., 'Industrialization is the path to prosperity.')\n"
    "- 🏛️ Regime characteristics (e.g., 'Bolivia is ruled by a corrupt dictatorship.')\n"
    "- 🆚 Us-vs-them framing (e.g., 'Global elites are trying to control ordinary citizens.')\n"
    "- 🧭 Value assertions (e.g., 'Freedom of speech is under attack in the West.')\n\n"
    "🚫 DO NOT EXTRACT:\n"
    "- ✔️ Polite sentiments (e.g., 'Minnesota is a great place with great people.')\n"
    "- 📅 Factual updates (e.g., 'A law was passed yesterday.')\n"
    "- 🔮 Future intentions (e.g., 'We will defeat our enemies.')\n"
    "- 🙏 Moral platitudes (e.g., 'Violence is bad.')\n"
    "- 🤝 Praise without ideology (e.g., 'Our soldiers are brave.')\n\n"
    "✍️ Guidelines:\n"
    "- Rewrite each extracted idea as a short, **clear, independent sentence**.\n"
    "- Do not quote directly.\n"
    "- No conjunctions like 'and', 'but', or 'or'. One claim per sentence.\n"
    "- Do not include questions, commands, or future promises.\n"
    "- Avoid any claim containing words like 'will', 'shall', 'is going to', or other future tense constructions.\n"
    "- Include only claims about the present or past — or those expressing ideological beliefs, accusations, or judgments.\n\n"
    "📦 Output format:\n"
    "Return ONLY a JSON object in the following format:\n"
    "{ \"narrative_claims\": [\"Claim 1.\", \"Claim 2.\", \"Claim 3.\"] }\n"
    "Return ONLY the JSON — no extra text, explanation, or commentary."
)


# -------------------------
# INTERNAL HELPER
# -------------------------

def _extract_with_prompt(text: str, system_prompt: str, model: str = "gpt-4o"):
    """
    Calls OpenAI Chat Completions and parses JSON response.
    Returns: (claims: list[str] | None, provider: str, model: str)
    """
    provider = "OpenAI"

    try:
        client = openai.OpenAI(api_key=openai.api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the text:\n{text}\nPlease extract narrative claims and return them in JSON."}
            ],
            temperature=0.3,
            max_tokens=700,
        )

        gpt_output = (response.choices[0].message.content or "").strip()

        # 1) try direct JSON parse
        try:
            data = json.loads(gpt_output)
        except json.JSONDecodeError:
            # 2) fallback: extract {...} block
            json_match = re.search(r"\{[\s\S]*\}", gpt_output)
            if not json_match:
                print(f"❌ Failed to parse GPT output as JSON: {gpt_output}")
                return None, provider, model
            data = json.loads(json_match.group(0))

        claims = data.get("narrative_claims", [])
        # normalize basic stuff
        if not isinstance(claims, list):
            return None, provider, model
        claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]

        return claims, provider, model

    except Exception as e:
        print(f"❌ OpenAI API error in narrative extraction: {e}")
        return None, provider, model


# -------------------------
# PUBLIC API (USED BY VIEWS)
# -------------------------

def extract_narrative_claims(text: str):
    """
    Main extractor used by backend right now.
    Uses ONLY crypto prompt (blockchain narratives).
    """
    return _extract_with_prompt(text=text, system_prompt=SYSTEM_PROMPT_CRYPTO, model="gpt-4o")


# -------------------------
# KEEP FOR LATER (NOT USED NOW)
# -------------------------

def extract_narrative_claims_ideology(text: str):
    """
    Ideology extractor kept for later use.
    Not referenced anywhere for now.
    """
    return _extract_with_prompt(text=text, system_prompt=SYSTEM_PROMPT_IDEOLOGY, model="gpt-4o")


def suggest_topics_for_text(text: str, topics_data: list):
    """
    Suggests topics for a given text using FlashText for high performance.
    No LLM calls to save tokens and avoid quota issues.
    """
    from flashtext import KeywordProcessor
    import re

    keyword_processor = KeywordProcessor(case_sensitive=False)
    
    # Map keywords/names to topic IDs
    # We store the original keyword to return it later
    keyword_to_topic = {} # { "keyword": topic_id }
    
    for t in topics_data:
        topic_id = str(t['id'])
        # Add topic name as a keyword
        name = t['name']
        keyword_processor.add_keyword(name, (topic_id, name))
        # Add all keywords
        for kw in t.get('keywords', []):
            if kw.strip():
                keyword_processor.add_keyword(kw.strip(), (topic_id, kw.strip()))

    # Extract keywords with their positions
    # Returns: [((topic_id, original_kw), start, end), ...]
    keywords_found = keyword_processor.extract_keywords(text, span_info=True)
    
    if not keywords_found:
        return []

    # Process findings to get unique topics and their context
    suggestions = []
    seen_topics = set()
    
    # Split text into sentences for better context extraction
    sentences = []
    for m in re.finditer(r'[^.!?]+[.!?]?', text):
        sentences.append({
            'text': m.group(),
            'start': m.start(),
            'end': m.end()
        })

    for (topic_id_str, matched_kw), start, end in keywords_found:
        topic_id = int(topic_id_str)
        if topic_id in seen_topics:
            continue
            
        # Find the sentence containing this span
        context = ""
        for s in sentences:
            if s['start'] <= start and s['end'] >= end:
                context = s['text'].strip()
                break
        
        # Ensure the keyword is actually in the context for highlighting
        if context and matched_kw.lower() not in context.lower():
            context = "" # Force fallback if keyword was lost in splitting

        if not context:
            # Fallback if sentence splitting is weird
            c_start = max(0, start - 100)
            c_end = min(len(text), end + 150)
            context = text[c_start:c_end].replace('\n', ' ').strip()
            if c_start > 0: context = "..." + context
            if c_end < len(text): context = context + "..."

        suggestions.append({
            "topic_id": topic_id,
            "matched_keyword": matched_kw,
            "context": context[:500]
        })
        seen_topics.add(topic_id)

    return suggestions
