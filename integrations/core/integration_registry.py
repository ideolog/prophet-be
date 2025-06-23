from .whitehouse_scraper import WhiteHouseScraper

INTEGRATION_REGISTRY = {
    "the-white-house": WhiteHouseScraper(),
}
# must exactly match your Source.slug
