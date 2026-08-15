import time

import httpx

from app import config
from app.providers.base import ProviderError, Quote, SearchRequest


class AmadeusProvider:
    """Cheapest offer from the Amadeus Flight Offers Search API.

    Uses the self-service OAuth2 client-credentials flow; tokens last 30 minutes
    and are cached until shortly before expiry.
    """

    name = "amadeus"

    def __init__(self, client_id: str = "", client_secret: str = "", base_url: str = "") -> None:
        self.client_id = client_id or config.AMADEUS_CLIENT_ID
        self.client_secret = client_secret or config.AMADEUS_CLIENT_SECRET
        self.base_url = (base_url or config.AMADEUS_BASE_URL).rstrip("/")
        self._token = ""
        self._token_expires_at = 0.0

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        if not self.client_id or not self.client_secret:
            raise ProviderError("AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are not set")

        response = await client.post(
            f"{self.base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            raise ProviderError(
                f"Amadeus auth failed: {response.status_code} {response.text[:200]}"
            )
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 1799)) - 60
        return self._token

    async def cheapest(self, request: SearchRequest) -> Quote | None:
        params = {
            "originLocationCode": request.origin,
            "destinationLocationCode": request.destination,
            "departureDate": request.depart_date.isoformat(),
            "adults": request.adults,
            "currencyCode": request.currency,
            "max": 20,
        }
        if request.return_date:
            params["returnDate"] = request.return_date.isoformat()

        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._access_token(client)
            response = await client.get(
                f"{self.base_url}/v2/shopping/flight-offers",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code != 200:
                raise ProviderError(
                    f"Amadeus search failed: {response.status_code} {response.text[:200]}"
                )
            offers = response.json().get("data", [])

        if not offers:
            return None

        best = min(offers, key=lambda offer: float(offer["price"]["grandTotal"]))
        carriers = {
            segment["carrierCode"]
            for itinerary in best.get("itineraries", [])
            for segment in itinerary.get("segments", [])
        }
        return Quote(
            price=float(best["price"]["grandTotal"]),
            currency=best["price"].get("currency", request.currency),
            carrier=",".join(sorted(carriers)) or None,
            deep_link=None,
        )
