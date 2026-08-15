from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass
class Quote:
    price: float
    currency: str
    carrier: str | None = None
    deep_link: str | None = None


@dataclass
class SearchRequest:
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    adults: int
    currency: str


class PriceProvider(Protocol):
    name: str

    async def cheapest(self, request: SearchRequest) -> Quote | None:
        """Return the cheapest quote for the itinerary, or None if unavailable."""


class ProviderError(RuntimeError):
    pass
