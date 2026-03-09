import wikipediaapi
import re

def fetch_wikipedia(topic_name: str, lang: str = 'en', wikipedia_url: str = None):
    """
    Fetches the summary and related links of a Wikipedia page for a given topic name or direct URL.
    """
    user_agent = "ProphetOntologyBot/1.0 (https://github.com/paulus/prophet; contact@example.com)"
    
    wiki = wikipediaapi.Wikipedia(
        user_agent=user_agent,
        language=lang,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    
    page = None
    if wikipedia_url:
        # Extract title from URL (e.g., https://en.wikipedia.org/wiki/Bitcoin -> Bitcoin)
        match = re.search(r'/wiki/([^/?#]+)', wikipedia_url)
        if match:
            page_title = match.group(1).replace('_', ' ')
            page = wiki.page(page_title)
    
    if not page or not page.exists():
        page = wiki.page(topic_name)
    
    if not page.exists():
        return None
    
    # Extract links from summary and overview
    # wikipedia-api doesn't provide section-specific links directly, 
    # but we can get all links and filter them by what's in the summary/overview text.
    
    summary_text = page.summary
    
    # Get the first section (often Overview or Introduction after summary)
    overview_text = ""
    if page.sections:
        first_section = page.sections[0]
        # Common names for the first section that is usually an overview
        if first_section.title.lower() in ['overview', 'history', 'background', 'description']:
            overview_text = first_section.text
    
    combined_discovery_text = (summary_text + " " + overview_text).lower()
    
    # Filter links that appear in the summary or overview
    related_links = []
    for title, link_page in page.links.items():
        if title.lower() in combined_discovery_text:
            related_links.append({
                "title": title,
                "url": link_page.fullurl
            })
    
    return {
        "source": "Wikipedia",
        "title": page.title,
        "content": summary_text[:2000],
        "url": page.fullurl,
        "related_links": related_links
    }
