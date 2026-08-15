from datetime import date, timedelta

DEPART = (date.today() + timedelta(days=60)).isoformat()

WATCH = {
    "origin": "hyd",
    "destination": "dxb",
    "depart_date": DEPART,
    "adults": 2,
    "currency": "usd",
    "target_price": 10000,
}


def test_health_reports_provider(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"


def test_create_normalises_codes_and_lists_watch(client):
    created = client.post("/api/watches", json=WATCH)
    assert created.status_code == 201
    body = created.json()
    assert (body["origin"], body["destination"], body["currency"]) == ("HYD", "DXB", "USD")

    listed = client.get("/api/watches").json()
    assert [watch["id"] for watch in listed] == [body["id"]]


def test_rejects_return_before_departure(client):
    earlier = (date.today() + timedelta(days=30)).isoformat()
    response = client.post("/api/watches", json={**WATCH, "return_date": earlier})
    assert response.status_code == 422


def test_check_records_history_and_alert_below_target(client):
    watch_id = client.post("/api/watches", json=WATCH).json()["id"]

    result = client.post(f"/api/watches/{watch_id}/check").json()
    assert result["price"] > 0
    assert result["alerted"] is True

    history = client.get(f"/api/watches/{watch_id}/prices").json()
    assert len(history) == 1

    alerts = client.get("/api/alerts").json()
    assert alerts[0]["watch_id"] == watch_id


def test_no_alert_when_price_above_target(client):
    watch_id = client.post("/api/watches", json={**WATCH, "target_price": 1}).json()["id"]
    assert client.post(f"/api/watches/{watch_id}/check").json()["alerted"] is False
    assert client.get("/api/alerts").json() == []


def test_paused_watch_is_skipped_by_check_all(client):
    watch_id = client.post("/api/watches", json=WATCH).json()["id"]
    client.post(f"/api/watches/{watch_id}/active?active=false")

    assert client.post("/api/check-all").json()["checked"] == 0

    client.post(f"/api/watches/{watch_id}/active?active=true")
    assert client.post("/api/check-all").json()["checked"] == 1


def test_delete_removes_watch_and_history(client):
    watch_id = client.post("/api/watches", json=WATCH).json()["id"]
    client.post(f"/api/watches/{watch_id}/check")

    assert client.delete(f"/api/watches/{watch_id}").status_code == 204
    assert client.get("/api/watches").json() == []
    assert client.get(f"/api/watches/{watch_id}/prices").status_code == 404
    assert client.delete(f"/api/watches/{watch_id}").status_code == 404
