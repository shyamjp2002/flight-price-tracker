from app import config
from app.providers.amadeus import AmadeusProvider
from app.providers.base import (
    DestinationQuote,
    PriceProvider,
    ProviderError,
    Quote,
    SearchRequest,
)
from app.providers.mock import MockProvider
from app.providers.travelpayouts import TravelpayoutsProvider

__all__ = [
    "AmadeusProvider",
    "DestinationQuote",
    "MockProvider",
    "PriceProvider",
    "ProviderError",
    "Quote",
    "SearchRequest",
    "TravelpayoutsProvider",
    "get_provider",
]

PROVIDERS = {
    "mock": MockProvider,
    "travelpayouts": TravelpayoutsProvider,
    "amadeus": AmadeusProvider,
}


def get_provider(name: str = "") -> PriceProvider:
    selected = (name or config.PROVIDER).lower()
    try:
        return PROVIDERS[selected]()
    except KeyError:
        raise ProviderError(f"Unknown price provider: {selected}") from None
