import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "flights.db"))

PROVIDER = os.environ.get("PRICE_PROVIDER", "mock")

TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN", "")

# Amadeus self-service was decommissioned in July 2026; kept for Enterprise keys.
AMADEUS_CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET", "")
AMADEUS_BASE_URL = os.environ.get("AMADEUS_BASE_URL", "https://test.api.amadeus.com")

CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))
ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "1") == "1"

MAX_FLEX_DAYS = int(os.environ.get("MAX_FLEX_DAYS", "3"))

DAILY_DIGEST = os.environ.get("DAILY_DIGEST", "0") == "1"
DIGEST_HOUR_UTC = int(os.environ.get("DIGEST_HOUR_UTC", "7"))

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_EMAIL_FROM = os.environ.get("ALERT_EMAIL_FROM", "")
ALERT_EMAIL_TO = [
    address.strip()
    for address in os.environ.get("ALERT_EMAIL_TO", "").split(",")
    if address.strip()
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ALERT_WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "")
