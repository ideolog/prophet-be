import wikipediaapi

def fetch_wikipedia(topic_name: str, lang: str = 'en'):
    """
    Fetches the summary of a Wikipedia page for a given topic name.
    """
    user_agent = "ProphetOntologyBot/1.0 (https://github.com/paulus/prophet; contact@example.com)"
    
    wiki = wikipediaapi.Wikipedia(
        user_agent=user_agent,
        language=lang,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    
    page = wiki.page(topic_name)
    
    if not page.exists():
        return None
    
    return {
        "source": "Wikipedia",
        "title": page.title,
        "content": page.summary[:2000],
        "url": page.fullurl
    }
