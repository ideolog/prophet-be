import abc

class IntegrationModule(abc.ABC):
    name = "UnnamedIntegration"

    @abc.abstractmethod
    def fetch_content(self, source_config: dict):
        """
        Fetch raw data from external source.
        source_config may contain URLs, credentials, API keys, etc.
        Returns raw data (usually HTML, JSON, etc.)
        """
        pass

    @abc.abstractmethod
    def normalize_to_rawtext(self, raw_data):
        """
        Normalize fetched raw data into standardized RawText-compatible dict.
        Returns list of dicts.
        """
        pass
