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
    2. NO PHRASES: Absolutely no verb phrases, no action descriptions (e.g., NO "Represent value", NO "Can be converted").
    3. SKIP IF COMPLEX: If a relation is described as a complex action, SKIP IT.
    4. PARENT (Strict): Only if [Topic] IS A [Parent]. (e.g., Bitcoin -> Cryptocurrency).
    5. SCHOOL (Strict): Only if explicitly stated "In [Field], ..." or similar.
    6. FUNCTIONS: Extract atomic nouns representing the role (e.g., "Medium of exchange", "Store of value").
    7. RELATED: Use this for important atomic concepts that don't fit as parents.
    
    Output MUST be a valid JSON object: {"parents": [], "schools": [], "functions": [], "related": []}.
    Use English only. Be extremely conservative.
    """
    
    prompt = f"Analyze this knowledge dossier for the topic '{topic_name}'. Identify its PARENT, SCHOOL OF THOUGHT, FUNCTIONS, and RELATED concepts. Use ONLY the provided text.\n\nDOSSIER:\n{knowledge_dossier}"
    
    return prompt_local_ai(prompt, system_prompt)

def suggest_new_topics_with_ai(text: str, existing_topics: list):
    """
    Analyzes a text to suggest new topics that are not in the existing_topics list.
    """
    system_prompt = """
    You are an expert crypto and blockchain ontology analyst. Your task is to identify key topics in a text that are NOT already in our database.
    
    CRITICAL RULES:
    1. ATOMIC NOUNS ONLY: Every topic must be a single, solid encyclopedic entity (e.g., "Yield Farming", "Zk-Rollup", "Governance").
    2. NO PHRASES: Absolutely no verb phrases, no action descriptions, no long sentences.
    3. NO DUPLICATES: Do not suggest topics that are already in the provided 'Existing Topics' list.
    4. ENCYCLOPEDIC: Only suggest things that likely have their own Wikipedia page or a dedicated entry in a crypto glossary.
    5. Output MUST be a valid JSON object with one key: "suggested_topics" (list of strings).
    6. Use English only. Be conservative.
    """
    
    existing_str = ", ".join(existing_topics)
    prompt = f"Identify new important topics in the following text. \n\nEXISTING TOPICS (DO NOT SUGGEST THESE): {existing_str}\n\nTEXT:\n{text}"
    
    return prompt_local_ai(prompt, system_prompt)
