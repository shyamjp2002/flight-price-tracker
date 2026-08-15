import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import airports, config, notifiers, service
from app.db import init_db
from app.models import (
    Airport,
    Alert,
    DestinationDeal,
    PricePoint,
    Watch,
    WatchCreate,
)
from app.providers import ProviderError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if config.ENABLE_SCHEDULER:
        scheduler.add_job(
            service.check_all_active,
            "interval",
            minutes=config.CHECK_INTERVAL_MINUTES,
            id="check_all_active",
            replace_existing=True,
        )
        if config.DAILY_DIGEST:
            scheduler.add_job(
                service.send_digest,
                "cron",
                hour=config.DIGEST_HOUR_UTC,
                minute=0,
                id="daily_digest",
                replace_existing=True,
            )
        scheduler.start()
        logger.info("scheduler started, every %s min", config.CHECK_INTERVAL_MINUTES)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Flight Price Tracker", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "provider": config.PROVIDER,
        "check_interval_minutes": config.CHECK_INTERVAL_MINUTES,
        "max_flex_days": config.MAX_FLEX_DAYS,
        "daily_digest": config.DAILY_DIGEST,
    }


@app.get("/api/watches", response_model=list[Watch])
async def get_watches() -> list[dict]:
    return service.list_watches()


@app.post("/api/watches", response_model=Watch, status_code=201)
async def post_watch(payload: WatchCreate) -> dict:
    return service.create_watch(payload.model_dump())


@app.delete("/api/watches/{watch_id}", status_code=204)
async def remove_watch(watch_id: int) -> None:
    if not service.delete_watch(watch_id):
        raise HTTPException(status_code=404, detail="watch not found")


@app.post("/api/watches/{watch_id}/active", response_model=Watch)
async def toggle_watch(watch_id: int, active: bool) -> dict:
    watch = service.set_active(watch_id, active)
    if watch is None:
        raise HTTPException(status_code=404, detail="watch not found")
    return watch


@app.get("/api/watches/{watch_id}/prices", response_model=list[PricePoint])
async def get_prices(watch_id: int) -> list[dict]:
    if service.get_watch(watch_id) is None:
        raise HTTPException(status_code=404, detail="watch not found")
    return service.price_history(watch_id)


@app.post("/api/watches/{watch_id}/check")
async def check_now(watch_id: int) -> dict:
    result = await service.check_watch(watch_id)
    if result is None:
        raise HTTPException(status_code=404, detail="watch not found or no offers available")
    return result


@app.post("/api/check-all")
async def check_all() -> dict:
    results = await service.check_all_active()
    return {"checked": len(results), "results": results}


@app.get("/api/alerts", response_model=list[Alert])
async def get_alerts() -> list[dict]:
    return service.list_alerts()


@app.get("/api/airports", response_model=list[Airport])
async def search_airports(q: str, limit: int = 8) -> list[dict]:
    return airports.search(q, limit=min(limit, 20))


@app.get("/api/explore", response_model=list[DestinationDeal])
async def explore(
    origin: str,
    depart_date: date,
    currency: str = "USD",
    max_price: float | None = None,
    limit: int = 10,
) -> list[dict]:
    """Cheapest destinations from an origin, for open-ended trips."""
    try:
        return await service.explore(
            origin, depart_date, currency, max_price, limit=min(limit, 30)
        )
    except ProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None


@app.get("/api/digest")
async def preview_digest() -> dict:
    return {"body": service.digest_body(), "enabled": config.DAILY_DIGEST}


@app.post("/api/digest/send")
async def send_digest() -> dict:
    return await service.send_digest()


@app.get("/api/notifications")
async def get_notification_channels() -> dict:
    return {"channels": [notifier.name for notifier in notifiers.active_notifiers()]}


@app.post("/api/notifications/test")
async def test_notifications() -> dict:
    delivered = await notifiers.dispatch(
        "Flight Price Tracker test alert",
        "This is a test notification from your flight price tracker.",
    )
    return {"delivered_to": delivered}


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
