import hashlib
import math
import random
from datetime import datetime, timezone

from app.providers.base import Quote, SearchRequest

CARRIERS = ["AI", "6E", "EK", "QR", "LH", "BA"]


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
            deep_link=(
                "https://www.google.com/travel/flights?q="
                f"flights%20{request.origin}%20to%20{request.destination}%20on%20{request.depart_date}"
            ),
        )
