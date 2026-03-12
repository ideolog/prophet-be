import requests
import json
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:9b")

def prompt_local_ai(prompt: str, system_prompt: str = None):
    """
    Sends a prompt to a local Ollama instance.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    if system_prompt:
        payload["system"] = system_prompt
        
    try:
        # Increase timeout for 9b model
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        # Ollama returns the generated text in the 'response' field
        content = result.get("response", "")
        return json.loads(content)
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        return None

def analyze_topic_with_ai(topic_name: str, knowledge_dossier: str):
    """
    Analyzes a knowledge dossier to extract ontology relations based on specific rules.
    """
    system_prompt = """
    You are a highly skeptical and critical ontology analyst. Your task is to extract ONLY atomic, encyclopedic concepts from the provided knowledge dossier.
    
    KNOWLEDGE PRIORITY:
    - If information from Binance Academy contradicts Wikipedia regarding crypto/blockchain terms, TRUST Binance Academy.
    - Use Wikipedia for broader hierarchical context (Parents/Schools).

    CRITICAL RULES:
    1. ATOMIC NOUNS ONLY: Every topic must be a single, solid encyclopedic entity (e.g., "Asset", "Cryptocurrency", "Liquidity").
    2. NO AMBIGUOUS SINGLE WORDS: If a concept is a single word with multiple meanings (e.g., "Vice", "De", "Gas"), prefer a more specific multi-word term (e.g., "Moral Vice", "Taoist De", "Transaction Fee").
    3. NO PHRASES: Absolutely no verb phrases, no action descriptions (e.g., NO "Represent value", NO "Can be converted").
    4. SKIP IF COMPLEX: If a relation is described as a complex action, SKIP IT.
    5. TYPE (Strict): Identify the classification type (e.g., "Person", "Crypto", "Organization", "Blockchain network").
    6. SCHOOL (Strict): Only if explicitly stated "In [Field], ..." or similar.
    7. RELATED: Use this for important atomic concepts that don't fit as type or school.
    
    Output MUST be a valid JSON object: {"type": "Type Name", "schools": [], "related": []}.
    Use English only. Be extremely conservative.
    """
    
    prompt = f"Analyze this knowledge dossier for the topic '{topic_name}'. Identify its TYPE, SCHOOL OF THOUGHT, and RELATED concepts. Use ONLY the provided text.\n\nDOSSIER:\n{knowledge_dossier}"
    
    return prompt_local_ai(prompt, system_prompt)

GEOGRAPHIC_ENTITY_RULES = """
    GEOGRAPHIC ENTITIES (when type_name is Region, State/Province, or City):
    - REGION: Identify geographic regions that appear in the text (e.g. Middle East, Far East, Southeast Asia, Latin America, Sub-Saharan Africa). Use common English names; no leading "The", no commas.
    - STATE/PROVINCE: Identify states, provinces, or first-level administrative regions (e.g. California, Texas, Ontario, Bavaria). For ambiguous names include context.
    - CITY: Always identify the COUNTRY (and when helpful the state/province) as context for disambiguation. Output format for cities (and for ambiguous states) must include:
      "context_country": "Country Name" (required for City),
      "context_region": "Region Name" (optional, e.g. Middle East),
      "context_state_province": "State or Province" (optional, for cities with same name in different states).
    - Use common names only (e.g. North Korea not Korea Democratic People's Republic). No commas in names. Do not start names with "The".
"""


def suggest_new_topics_with_ai(text: str, existing_topics: list, topic_types: list = None):
    """
    Analyzes a text to suggest new topics that are not in the existing_topics list.
    topic_types: optional list of {"id": int, "name": str} so the AI can suggest a valid type per topic.
    Returns: {"suggested_topics": [{"name": "...", "type_name": "..." or null, "context_country"?: "...", "context_region"?: "...", "context_state_province"?: "..."}, ...]} or legacy.
    """
    topic_types = topic_types or []
    type_list_str = ""
    if topic_types:
        names = [t.get("name") or str(t) for t in topic_types if t]
        type_list_str = (
            "\n\nAVAILABLE TOPIC TYPES (use exact name for type_name when relevant; or null if none fit):\n"
            + ", ".join(sorted(set(names)))
            + "\nFor each suggested topic, choose the most appropriate type from this list if one fits (e.g. Person, Organization, COUNTRY, Region, State/Province, City, Process, Theory). Use the exact type name."
        )

    system_prompt = """
    You are an expert crypto and blockchain ontology analyst. Your task is to identify key topics in a text that are NOT already in our database.

    CRITICAL RULES:
    1. ATOMIC NOUNS ONLY: Every topic must be a single, solid encyclopedic entity (e.g., "Yield Farming", "Zk-Rollup", "Governance").
    2. NO AMBIGUOUS SINGLE WORDS: If a concept is a single word with multiple meanings (e.g., "Vice", "De", "Gas"), prefer a more specific multi-word term (e.g., "Moral Vice", "Taoist De", "Transaction Fee").
    3. COLLECTIVE ACTORS: Identify groups or categories of actors (e.g., "Whales", "Holders", "Retail Investors", "Regulators").
    4. NARRATIVE THEMES: Identify important market sentiment themes (e.g., "Bull Market", "Bear Market", "Hyperinflation").
    5. NO TICKERS: Do not suggest tickers like "BTC", "ETH", "SOL" as new topics.
    6. NO PHRASES: Absolutely no verb phrases, no action descriptions, no long sentences.
    7. FOCUS ON CONCEPTS: Focus on technologies, economic theories, processes, and abstract themes.
       - Specific Names of People and Organizations are handled by a separate system, so you can skip them unless they are extremely critical to the ontology itself.
    8. NO DUPLICATES: Do not suggest topics that are already in the provided 'Existing Topics' list.
    9. ENCYCLOPEDIC: Only suggest things that likely have their own Wikipedia page or a dedicated entry in a crypto glossary.
    10. Output MUST be a valid JSON object: "suggested_topics" = list of objects. Each object: "name" (string), optionally "type_name" (string from the available types list, or null). For type_name City (and for ambiguous State/Province) also include "context_country", and optionally "context_region", "context_state_province".
    11. Use English only. Be conservative.
    """ + type_list_str + GEOGRAPHIC_ENTITY_RULES

    existing_str = ", ".join(existing_topics)
    prompt = f"Identify new important topics in the following text.\n\nEXISTING TOPICS (DO NOT SUGGEST THESE): {existing_str}\n\nTEXT:\n{text}"
    
    return prompt_local_ai(prompt, system_prompt)

def suggest_topic_merge_with_ai(topics_list: list):
    """
    Analyzes a list of topics to suggest a potential merge between two similar topics.
    """
    system_prompt = """
    You are an expert ontology cleaner. Your task is to find two topics in a list that represent the same concept and should be merged.
    
    CRITICAL RULES:
    1. FIND DUPLICATES: Look for synonyms, different spellings, or very closely related concepts that should be a single entry (e.g., "BTC" and "Bitcoin", "Smart Contract" and "Smart Contracts").
    2. BE PRECISE: Only suggest a merge if you are 95% sure they are the same thing.
    3. Output MUST be a valid JSON object with the following structure:
       {
         "source_topic": {"id": 123, "name": "Topic A"},
         "target_topic": {"id": 456, "name": "Topic B"},
         "reason": "Explanation of why they should be merged"
       }
    4. If no merge is found, return an empty object: {}.
    5. Use English only.
    """
    
    topics_str = "\n".join([f"ID: {t['id']}, Name: {t['name']}" for t in topics_list])
    prompt = f"Find two topics in this list that should be merged into one:\n\n{topics_str}"
    
    return prompt_local_ai(prompt, system_prompt)

def analyze_swot_trigger(topic_name: str, context: str, author_name: str = "the author"):
    """
    Analyzes a specific mention of a SWOT/Threat topic in a text to fill a survey-like questionnaire.
    """
    system_prompt = f"""
    You are a socio-political analyst conducting a survey of {author_name}'s opinions based on their text.
    Your task is to analyze how the author discusses a specific topic: "{topic_name}".
    
    You must fill out a "Risk/Threat Survey" with the following fields:
    1. PESTEL Category: Choose exactly ONE from: Political, Economic, Social, Technological, Environmental, Legal.
    2. Impact Strength: How serious is this threat/issue according to the author? 
       - 1: Low (minor concern)
       - 2: Medium (significant)
       - 3: High (serious threat)
       - 4: Critical (existential risk, "biggest threat")
    3. Stance: Does the author agree that this is a real and dangerous threat?
       - -2: Strongly Disagree (denies the threat, mocks it, "fake news")
       - -1: Disagree (thinks it's overblown)
       -  0: Neutral (just mentions it without clear opinion)
       - +1: Agree (acknowledges it's a real issue)
       - +2: Strongly Agree (fully convinced it's a major danger)
    4. Summary: A very short (1 sentence) explanation of the author's specific point about this topic.

    Output MUST be a valid JSON object:
    {{
        "pestel_category": "Category",
        "impact_strength": 1-4,
        "stance": -2 to 2,
        "summary": "Short explanation"
    }}
    """
    
    prompt = f"Analyze how {author_name} discusses '{topic_name}' in the following context:\n\nCONTEXT:\n{context}"
    
    return prompt_local_ai(prompt, system_prompt)
