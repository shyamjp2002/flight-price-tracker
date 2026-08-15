"""Airport lookup for typeahead search by IATA code, city, or airport name."""

from dataclasses import dataclass
from functools import lru_cache

import airportsdata


@dataclass(frozen=True)
class Airport:
    iata: str
    name: str
    city: str
    country: str

    def as_dict(self) -> dict:
        return {"iata": self.iata, "name": self.name, "city": self.city, "country": self.country}


@lru_cache(maxsize=1)
def _airports() -> list[Airport]:
    """Every airport with an IATA code, biggest-city-first tie-breaking left to search()."""
    return [
        Airport(iata=code, name=entry["name"], city=entry["city"], country=entry["country"])
        for code, entry in sorted(airportsdata.load("IATA").items())
    ]


def get(iata: str) -> Airport | None:
    code = iata.strip().upper()
    return next((airport for airport in _airports() if airport.iata == code), None)


def label(iata: str) -> str:
    """'HYD (Hyderabad)' when known, otherwise just the code."""
    airport = get(iata)
    return f"{iata} ({airport.city})" if airport and airport.city else iata


def _rank(airport: Airport, needle: str) -> int | None:
    """How well an airport matches a lowercase needle; lower is better, None is no match."""
    city = airport.city.lower()
    name = airport.name.lower()
    if airport.iata.lower() == needle:
        return 0
    if city.startswith(needle):
        return 1
    if any(word.startswith(needle) for word in city.split()):
        return 2
    if name.startswith(needle):
        return 3
    if needle in city or needle in name:
        return 4
    return None


def search(query: str, limit: int = 8) -> list[dict]:
    """Airports matching a code, city, or name, best match first."""
    needle = query.strip().lower()
    if len(needle) < 2:
        return []

    scored = []
    for airport in _airports():
        rank = _rank(airport, needle)
        if rank is not None:
            major = 0 if "international" in airport.name.lower() else 1
            scored.append((rank, major, airport.city, airport.iata, airport))

    scored.sort(key=lambda item: item[:4])
    return [item[-1].as_dict() for item in scored[:limit]]
