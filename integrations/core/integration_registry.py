from .whitehouse_scraper import WhiteHouseScraper
from .coindesk_scraper import CoinDeskScraper
from integrations.sources.youtube import YouTubeIntegration

INTEGRATION_REGISTRY = {
    "the-white-house": WhiteHouseScraper(),
    "youtube": YouTubeIntegration(),
    "coindesk": CoinDeskScraper(),
}
# must exactly match your Source.slug
