from .wikipedia import fetch_wikipedia
from .binance_academy import fetch_binance_academy

def collect_topic_knowledge(topic_name: str):
    """
    Collects knowledge about a topic from multiple sources.
    """
    results = []
    
    # 1. Try Binance Academy (High Priority for Crypto)
    binance_data = fetch_binance_academy(topic_name)
    if binance_data:
        results.append(binance_data)
        
    # 2. Try Wikipedia (Broad Context)
    wiki_data = fetch_wikipedia(topic_name)
    if wiki_data:
        results.append(wiki_data)
        
    return results

def format_knowledge_dossier(knowledge_list):
    """
    Formats the collected knowledge into a string for the AI prompt.
    """
    if not knowledge_list:
        return "No information found in external sources."
        
    dossier = ""
    for item in knowledge_list:
        dossier += f"--- SOURCE: {item['source']} ---\n"
        dossier += f"TITLE: {item['title']}\n"
        dossier += f"CONTENT: {item['content']}\n\n"
        
    return dossier
