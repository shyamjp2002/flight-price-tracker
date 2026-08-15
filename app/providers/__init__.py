from app import config
from app.providers.amadeus import AmadeusProvider
from app.providers.base import PriceProvider, ProviderError, Quote, SearchRequest
from app.providers.mock import MockProvider

__all__ = [
    "AmadeusProvider",
    "MockProvider",
    "PriceProvider",
    "ProviderError",
    "Quote",
    "SearchRequest",
    "get_provider",
]


def get_provider(name: str = "") -> PriceProvider:
    selected = (name or config.PROVIDER).lower()
    if selected == "amadeus":
        return AmadeusProvider()
    if selected == "mock":
        return MockProvider()
    raise ProviderError(f"Unknown price provider: {selected}")
