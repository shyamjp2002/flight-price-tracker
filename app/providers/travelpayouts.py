from datetime import date

import httpx

from app import config
from app.providers.base import (
    DestinationQuote,
    ProviderError,
    Quote,
    SearchRequest,
    google_flights_link,
)

BASE_URL = "https://api.travelpayouts.com"
AVIASALES_URL = "https://www.aviasales.com"


class TravelpayoutsProvider:
    """Real fares from the Travelpayouts (Aviasales) flight data API.

    Prices come from cached search results rather than a live GDS, which suits a
    tracker: one cheap request per route per check, and a free token with no card.
    Replaces the Amadeus self-service API, decommissioned in July 2026.
    """

    name = "travelpayouts"

    def __init__(self, token: str = "") -> None:
        self.token = token or config.TRAVELPAYOUTS_TOKEN

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ProviderError("TRAVELPAYOUTS_TOKEN is not set")
        return {"X-Access-Token": self.token}

    async def _get(self, path: str, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{BASE_URL}{path}", params=params, headers=self._headers()
                )
            except httpx.HTTPError as error:
                raise ProviderError(
                    f"Travelpayouts request failed: {type(error).__name__}"
                ) from None
        if response.status_code != 200:
            raise ProviderError(
                f"Travelpayouts {path} failed: {response.status_code} {response.text[:200]}"
            )
        payload = response.json()
        if not payload.get("success", True):
            raise ProviderError(f"Travelpayouts {path} failed: {payload.get('error')}")
        return payload

    def _link(self, offer: dict, origin: str, destination: str, depart_date: date) -> str:
        relative = offer.get("link")
        return f"{AVIASALES_URL}{relative}" if relative else google_flights_link(
            origin, destination, depart_date
        )

    async def cheapest(self, request: SearchRequest) -> Quote | None:
        params = {
            "origin": request.origin,
            "destination": request.destination,
            "departure_at": request.depart_date.isoformat(),
            "currency": request.currency.lower(),
            "sorting": "price",
            "limit": 1,
            "one_way": "false" if request.return_date else "true",
        }
        if request.return_date:
            params["return_at"] = request.return_date.isoformat()

        offers = (await self._get("/aviasales/v3/prices_for_dates", params)).get("data") or []
        if not offers:
            return None

        best = min(offers, key=lambda offer: float(offer["price"]))
        # Quoted per passenger; adults > 1 is not supported upstream, so scale it.
        price = float(best["price"]) * request.adults
        return Quote(
            price=round(price, 2),
            currency=request.currency,
            carrier=best.get("airline"),
            deep_link=self._link(best, request.origin, request.destination, request.depart_date),
        )

    async def destinations(
        self, origin: str, depart_date: date, currency: str, limit: int
    ) -> list[DestinationQuote]:
        """City Directions: cheapest destinations found from an origin recently."""
        params = {"origin": origin, "currency": currency.lower()}
        data = (await self._get("/v1/city-directions", params)).get("data") or {}

        quotes = []
        for destination, offer in data.items():
            departure = offer.get("departure_at", "")[:10]
            quotes.append(
                DestinationQuote(
                    destination=destination,
                    price=float(offer["price"]),
                    currency=currency.upper(),
                    depart_date=date.fromisoformat(departure) if departure else depart_date,
                    return_date=(
                        date.fromisoformat(offer["return_at"][:10])
                        if offer.get("return_at")
                        else None
                    ),
                    deep_link=self._link(offer, origin, destination, depart_date),
                )
            )
        quotes.sort(key=lambda item: item.price)
        return quotes[:limit]
