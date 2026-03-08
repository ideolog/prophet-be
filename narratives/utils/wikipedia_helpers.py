import wikipediaapi

def get_wikipedia_summary(topic_name: str, lang: str = 'en'):
    """
    Fetches the summary of a Wikipedia page for a given topic name.
    """
    # Wikipedia API requires a user agent
    user_agent = "ProphetOntologyBot/1.0 (https://github.com/paulus/prophet; contact@example.com)"
    
    wiki = wikipediaapi.Wikipedia(
        user_agent=user_agent,
        language=lang,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    
    page = wiki.page(topic_name)
    
    if not page.exists():
        # Try searching if exact match doesn't exist? 
        # For now, let's just return None to keep it simple as requested.
        return None
    
    return {
        "title": page.title,
        "summary": page.summary[:2000], # Limit summary length
        "full_url": page.fullurl
    }
