import asyncio
from datetime import date, timedelta

from app import airports, insights
from app.providers.base import SearchRequest

DEPART = (date.today() + timedelta(days=60)).isoformat()

WATCH = {
    "origin": "HYD",
    "destination": "DXB",
    "depart_date": DEPART,
    "adults": 1,
    "currency": "USD",
    "target_price": None,
}


def test_airport_search_matches_city_and_code():
    by_city = airports.search("hyderabad")
    assert "HYD" in [airport["iata"] for airport in by_city]

    by_code = airports.search("dxb")
    assert by_code[0]["iata"] == "DXB"
    assert by_code[0]["city"]


def test_airport_label_falls_back_to_code():
    assert "Dubai" in airports.label("DXB")
    assert airports.label("ZZZ") == "ZZZ"


def test_recommendation_needs_history():
    assert insights.recommend([]).verdict == "watch"
    assert insights.recommend([100.0, 90.0]).verdict == "watch"


def test_recommendation_buys_at_target():
    result = insights.recommend([500.0, 480.0, 460.0], target_price=470.0)
    assert result.verdict == "buy"


def test_recommendation_waits_while_falling():
    falling = [600.0, 580.0, 560.0, 540.0, 500.0]
    assert insights.recommend(falling).verdict == "wait"


def test_recommendation_buys_near_the_low():
    steady = [410.0, 405.0, 402.0, 403.0, 404.0, 402.0, 403.0]
    assert insights.recommend(steady).verdict == "buy"


def test_flexible_search_keeps_trip_length_and_skips_past_dates():
    from app import service
    from app.providers import get_provider

    depart = date.today() + timedelta(days=30)
    request = SearchRequest(
        origin="HYD",
        destination="DXB",
        depart_date=depart,
        return_date=depart + timedelta(days=7),
        adults=1,
        currency="USD",
    )
    quote, for_date = asyncio.run(
        service.cheapest_flexible(get_provider("mock"), request, flex_days=3)
    )
    assert quote is not None
    assert abs((for_date - depart).days) <= 3

    tomorrow = date.today() + timedelta(days=1)
    near = SearchRequest(
        origin="HYD",
        destination="DXB",
        depart_date=tomorrow,
        return_date=None,
        adults=1,
        currency="USD",
    )
    _, near_date = asyncio.run(service.cheapest_flexible(get_provider("mock"), near, flex_days=3))
    assert near_date >= date.today()


def test_flex_watch_records_selected_date(client):
    watch_id = client.post("/api/watches", json={**WATCH, "flex_days": 3}).json()["id"]
    result = client.post(f"/api/watches/{watch_id}/check").json()

    assert abs((date.fromisoformat(result["for_date"]) - date.fromisoformat(DEPART)).days) <= 3
    assert client.get(f"/api/watches/{watch_id}/prices").json()[0]["for_date"]


def test_watch_carries_labels_and_recommendation(client):
    client.post("/api/watches", json=WATCH)
    watch = client.get("/api/watches").json()[0]

    assert "Hyderabad" in watch["origin_label"]
    assert watch["recommendation"]["verdict"] in {"buy", "wait", "watch"}


def test_airports_endpoint(client):
    found = client.get("/api/airports", params={"q": "dubai"}).json()
    assert "DXB" in [airport["iata"] for airport in found]


def test_explore_endpoint_respects_max_price(client):
    deals = client.get(
        "/api/explore",
        params={"origin": "HYD", "depart_date": DEPART, "max_price": 400},
    ).json()

    assert deals
    assert all(deal["price"] <= 400 for deal in deals)
    assert all(deal["destination"] != "HYD" for deal in deals)
    assert deals == sorted(deals, key=lambda deal: deal["price"])


def test_digest_summarises_watches(client):
    assert "No watches yet" in client.get("/api/digest").json()["body"]

    watch_id = client.post("/api/watches", json=WATCH).json()["id"]
    client.post(f"/api/watches/{watch_id}/check")

    body = client.get("/api/digest").json()["body"]
    assert "Hyderabad" in body
    assert "Dubai" in body


def test_past_departure_date_is_rejected(client):
    past = (date.today() - timedelta(days=5)).isoformat()
    response = client.post("/api/watches", json={**WATCH, "depart_date": past})

    assert response.status_code == 422
    assert "past" in response.text


def test_digest_reports_delivery_failure(client, monkeypatch):
    from app import config, notifiers

    async def boom(self, subject: str, body: str) -> None:
        raise RuntimeError("smtp down")

    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    monkeypatch.setattr(notifiers.WebhookNotifier, "send", boom)

    result = client.post("/api/digest/send").json()

    assert result["delivered_to"] == []
    assert result["delivery_errors"] == ["webhook: smtp down"]
