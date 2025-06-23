import requests
from integrations.core.base_integration import IntegrationModule
from integrations.translators.whitehouse_translator import WhiteHouseTranslator

class WhiteHouseScraper(IntegrationModule):
    name = "WhiteHouseScraper"

    def fetch_content(self, source_config):
        base_url = "https://www.whitehouse.gov/briefings-statements/"
        page = source_config.get("page", 1)

        if page == 1:
            url = base_url
        else:
            url = f"{base_url}page/{page}/"

        response = requests.get(url)
        response.raise_for_status()

        # TEMP DEBUG
        with open("fetched_whitehouse.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        return response.text

    def normalize_to_rawtext(self, raw_html, source_config):
        translator = WhiteHouseTranslator()
        timezone = source_config.get("timezone", "UTC")
        return translator.parse(raw_html, source_timezone=timezone)

