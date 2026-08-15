import asyncio

import httpx
import pytest

from app import config, notifiers

from .test_api import WATCH


@pytest.fixture()
def clear_channels(monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "")
    monkeypatch.setattr(config, "ALERT_EMAIL_TO", [])
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "")


def test_no_channels_configured(clear_channels):
    assert notifiers.active_notifiers() == []


def test_channels_activate_when_configured(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(config, "ALERT_EMAIL_TO", ["me@example.com"])
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")

    assert [n.name for n in notifiers.active_notifiers()] == ["email", "telegram", "webhook"]


class FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.logged_in = False
        self.tls = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def starttls(self):
        self.tls = True

    def login(self, username, password):
        self.logged_in = True

    def send_message(self, message):
        FakeSMTP.sent.append(message)


def test_email_notifier_sends_over_starttls(clear_channels, monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(config, "SMTP_PORT", 587)
    monkeypatch.setattr(config, "SMTP_USERNAME", "user@example.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(config, "ALERT_EMAIL_FROM", "bot@example.com")
    monkeypatch.setattr(config, "ALERT_EMAIL_TO", ["a@example.com", "b@example.com"])
    monkeypatch.setattr(notifiers.smtplib, "SMTP", FakeSMTP)

    asyncio.run(notifiers.EmailNotifier().send("Fare alert", "HYD→DXB dropped"))

    message = FakeSMTP.sent[0]
    assert message["Subject"] == "Fare alert"
    assert message["From"] == "bot@example.com"
    assert message["To"] == "a@example.com, b@example.com"
    assert "HYD→DXB dropped" in message.get_content()


def test_telegram_notifier_posts_message(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    _patch_transport(monkeypatch, handler)
    asyncio.run(notifiers.TelegramNotifier().send("Fare alert", "cheap"))

    assert calls[0].url.path == "/bottok/sendMessage"


def test_telegram_notifier_raises_on_error(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    _patch_transport(monkeypatch, handler)
    with pytest.raises(RuntimeError):
        asyncio.run(notifiers.TelegramNotifier().send("Fare alert", "cheap"))


def test_telegram_transport_error_hides_token(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "supersecrettoken")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("failed to connect", request=request)

    _patch_transport(monkeypatch, handler)
    with pytest.raises(RuntimeError) as raised:
        asyncio.run(notifiers.TelegramNotifier().send("Fare alert", "cheap"))

    assert "supersecrettoken" not in str(raised.value)


def test_webhook_notifier_posts_json(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    bodies = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content.decode())
        return httpx.Response(204)

    _patch_transport(monkeypatch, handler)
    asyncio.run(notifiers.WebhookNotifier().send("Fare alert", "cheap"))

    assert "Fare alert" in bodies[0]


def test_dispatch_isolates_failing_channel(clear_channels, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")

    async def handler(request: httpx.Request) -> httpx.Response:
        if "telegram" in request.url.host:
            return httpx.Response(500, text="boom")
        return httpx.Response(200)

    _patch_transport(monkeypatch, handler)
    result = asyncio.run(notifiers.dispatch("Fare alert", "cheap"))

    assert result.delivered == ["webhook"]
    assert len(result.failed) == 1
    assert result.failed[0].startswith("telegram: ")


def test_check_records_alert_when_notification_fails(client, monkeypatch):
    async def boom(self, subject: str, body: str) -> None:
        raise RuntimeError("smtp down")

    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    monkeypatch.setattr(notifiers.WebhookNotifier, "send", boom)

    watch_id = client.post("/api/watches", json=WATCH).json()["id"]
    result = client.post(f"/api/watches/{watch_id}/check").json()

    assert result["alerted"] is True
    assert result["delivered_to"] == []
    assert result["delivery_errors"] == ["webhook: smtp down"]
    assert client.get("/api/alerts").json()[0]["delivered_to"] == ""


def test_notification_channels_endpoint(client, monkeypatch):
    assert client.get("/api/notifications").json() == {"channels": []}

    monkeypatch.setattr(config, "ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    assert client.get("/api/notifications").json() == {"channels": ["webhook"]}


def _patch_transport(monkeypatch, handler) -> None:
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
