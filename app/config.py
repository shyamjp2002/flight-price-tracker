import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "flights.db"))

PROVIDER = os.environ.get("PRICE_PROVIDER", "mock")
AMADEUS_CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET", "")
AMADEUS_BASE_URL = os.environ.get("AMADEUS_BASE_URL", "https://test.api.amadeus.com")

CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))
ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "1") == "1"
