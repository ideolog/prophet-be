from .whitehouse_scraper import WhiteHouseScraper
from .coindesk_scraper import CoinDeskIntegration
from .vitalik_scraper import VitalikIntegration
from integrations.sources.youtube import YouTubeIntegration

INTEGRATION_REGISTRY = {
    "the-white-house": WhiteHouseScraper(),
    "youtube": YouTubeIntegration(),
    "coindesk": CoinDeskIntegration(),
    "vitalik-ca": VitalikIntegration(),
}
# must exactly match your Source.slug
