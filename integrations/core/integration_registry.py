from .whitehouse_scraper import WhiteHouseScraper
from integrations.sources.youtube import YouTubeIntegration

INTEGRATION_REGISTRY = {
    "the-white-house": WhiteHouseScraper(),
    "youtube": YouTubeIntegration(),
}
# must exactly match your Source.slug
