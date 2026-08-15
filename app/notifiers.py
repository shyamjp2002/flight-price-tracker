import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import httpx

from app import config

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    name: str

    async def send(self, subject: str, body: str) -> None:
        """Deliver one alert. Raises on failure."""


class EmailNotifier:
    """Sends alerts over SMTP (STARTTLS when the port is not 465)."""

    name = "email"

    def __init__(self) -> None:
        self.host = config.SMTP_HOST
        self.port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.sender = config.ALERT_EMAIL_FROM or config.SMTP_USERNAME
        self.recipients = config.ALERT_EMAIL_TO

    async def send(self, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message.set_content(body)

        smtp_class = smtplib.SMTP_SSL if self.port == 465 else smtplib.SMTP
        with smtp_class(self.host, self.port, timeout=30) as smtp:
            if self.port != 465:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


class TelegramNotifier:
    name = "telegram"

    def __init__(self) -> None:
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    async def send(self, subject: str, body: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": f"{subject}\n{body}"},
                )
        except httpx.HTTPError as error:
            raise RuntimeError(f"Telegram request failed: {type(error).__name__}") from None
        if response.status_code != 200:
            raise RuntimeError(
                f"Telegram send failed: {response.status_code} {response.text[:200]}"
            )


class WebhookNotifier:
    """POSTs the alert as JSON, so Slack/Discord/Zapier hooks all work."""

    name = "webhook"

    def __init__(self) -> None:
        self.url = config.ALERT_WEBHOOK_URL

    async def send(self, subject: str, body: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                self.url, json={"subject": subject, "text": f"{subject}\n{body}"}
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Webhook send failed: {response.status_code} {response.text[:200]}")


def active_notifiers() -> list[Notifier]:
    """Build the notifiers whose configuration is complete."""
    notifiers: list[Notifier] = []
    if config.SMTP_HOST and config.ALERT_EMAIL_TO:
        notifiers.append(EmailNotifier())
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        notifiers.append(TelegramNotifier())
    if config.ALERT_WEBHOOK_URL:
        notifiers.append(WebhookNotifier())
    return notifiers


@dataclass
class DispatchResult:
    delivered: list[str]
    failed: list[str]

    @property
    def configured(self) -> bool:
        return bool(self.delivered or self.failed)


async def dispatch(subject: str, body: str) -> DispatchResult:
    """Send an alert to every configured channel, reporting per-channel failures."""
    result = DispatchResult(delivered=[], failed=[])
    for notifier in active_notifiers():
        try:
            await notifier.send(subject, body)
            result.delivered.append(notifier.name)
        except Exception as error:
            logger.exception("notifier %s failed", notifier.name)
            result.failed.append(f"{notifier.name}: {_reason(error)}")
    return result


def _reason(error: Exception) -> str:
    """A short, credential-free explanation of why a send failed."""
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return "SMTP login rejected (check SMTP_USERNAME and the app password)"
    if isinstance(error, smtplib.SMTPException | OSError):
        return f"SMTP error ({type(error).__name__})"
    return str(error) or type(error).__name__
