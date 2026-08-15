import hashlib
import math
import random
from datetime import date, datetime, timezone

from app.providers.base import (
    DestinationQuote,
    Quote,
    SearchRequest,
    google_flights_link,
)

CARRIERS = ["AI", "6E", "EK", "QR", "LH", "BA"]
POPULAR_DESTINATIONS = [
    "DXB",
    "SIN",
    "BKK",
    "KUL",
    "DOH",
    "AUH",
    "CMB",
    "KTM",
    "MLE",
    "HKG",
    "LHR",
    "IST",
    "JFK",
    "CDG",
    "SYD",
]


def _seed(request: SearchRequest) -> int:
    key = f"{request.origin}{request.destination}{request.depart_date}{request.return_date}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


class MockProvider:
    """Deterministic pseudo-random prices so the app is usable without API keys.

    The base fare depends on the route; a slow sine wave plus jitter simulates
    day-to-day movement, so watches show a realistic price history.
    """

    name = "mock"

    async def cheapest(self, request: SearchRequest) -> Quote | None:
        rng = random.Random(_seed(request))
        base = 120 + rng.random() * 600
        if request.return_date:
            base *= 1.8
        base *= 1 + 0.15 * (request.adults - 1)

        seconds = datetime.now(timezone.utc).timestamp()
        wave = math.sin(seconds / 43200 + rng.random() * math.pi) * 0.08
        jitter = random.Random(int(seconds)).uniform(-0.04, 0.04)
        price = round(base * (1 + wave + jitter), 2)

        return Quote(
            price=price,
            currency=request.currency,
            carrier=rng.choice(CARRIERS),
            deep_link=google_flights_link(
                request.origin, request.destination, request.depart_date
            ),
        )

    async def destinations(
        self, origin: str, depart_date: date, currency: str, limit: int
    ) -> list[DestinationQuote]:
        quotes = []
        for destination in POPULAR_DESTINATIONS:
            if destination == origin.upper():
                continue
            request = SearchRequest(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=None,
                adults=1,
                currency=currency,
            )
            quote = await self.cheapest(request)
            if quote is None:
                continue
            quotes.append(
                DestinationQuote(
                    destination=destination,
                    price=quote.price,
                    currency=quote.currency,
                    depart_date=depart_date,
                    deep_link=quote.deep_link,
                )
            )
        quotes.sort(key=lambda item: item.price)
        return quotes[:limit]
