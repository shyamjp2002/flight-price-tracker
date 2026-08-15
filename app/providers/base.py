from dataclasses import dataclass
from datetime import date
from typing import Protocol
from urllib.parse import quote_plus


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


@dataclass
class DestinationQuote:
    """Cheapest fare to one destination, for open-ended "anywhere from X" searches."""

    destination: str
    price: float
    currency: str
    depart_date: date
    return_date: date | None = None
    deep_link: str | None = None


class PriceProvider(Protocol):
    name: str

    async def cheapest(self, request: SearchRequest) -> Quote | None:
        """Return the cheapest quote for the itinerary, or None if unavailable."""

    async def destinations(
        self, origin: str, depart_date: date, currency: str, limit: int
    ) -> list[DestinationQuote]:
        """Return the cheapest destinations reachable from an origin around a date."""


class ProviderError(RuntimeError):
    pass


def google_flights_link(origin: str, destination: str, depart_date: date) -> str:
    """Search link for booking, since fare APIs do not hand out bookable URLs."""
    query = f"flights {origin} to {destination} on {depart_date}"
    return "https://www.google.com/travel/flights?q=" + quote_plus(query)
