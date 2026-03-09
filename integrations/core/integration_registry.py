from .whitehouse_scraper import WhiteHouseScraper
from .coindesk_scraper import CoinDeskIntegration
from .vitalik_scraper import VitalikIntegration
from .crypto_news_integrations import TheBlockIntegration, DecryptIntegration, CoinTelegraphIntegration
from integrations.sources.youtube import YouTubeIntegration

INTEGRATION_REGISTRY = {
    "the-white-house": WhiteHouseScraper(),
    "youtube": YouTubeIntegration(),
    "coindesk": CoinDeskIntegration(),
    "vitalik-ca": VitalikIntegration(),
    "the-block": TheBlockIntegration(),
    "decrypt": DecryptIntegration(),
    "cointelegraph": CoinTelegraphIntegration(),
}
# must exactly match your Source.slug
