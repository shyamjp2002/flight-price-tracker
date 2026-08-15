import logging
import sqlite3
from datetime import date, timedelta

from app import airports, config, insights, notifiers
from app.db import session
from app.providers import DestinationQuote, ProviderError, Quote, SearchRequest, get_provider

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _search_request(row: sqlite3.Row) -> SearchRequest:
    return SearchRequest(
        origin=row["origin"],
        destination=row["destination"],
        depart_date=date.fromisoformat(row["depart_date"]),
        return_date=_parse_date(row["return_date"]),
        adults=row["adults"],
        currency=row["currency"],
    )


def list_watches() -> list[dict]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT w.*,
                   (SELECT price FROM prices p WHERE p.watch_id = w.id
                     ORDER BY p.checked_at DESC, p.id DESC LIMIT 1) AS latest_price,
                   (SELECT MIN(price) FROM prices p WHERE p.watch_id = w.id) AS lowest_price,
                   (SELECT COUNT(*) FROM prices p WHERE p.watch_id = w.id) AS checks
            FROM watches w
            ORDER BY w.id DESC
            """
        ).fetchall()
    return [_decorate(dict(row)) for row in rows]


def _decorate(watch: dict) -> dict:
    """Add city labels and the buy-or-wait recommendation to a stored watch row."""
    prices = [point["price"] for point in price_history(watch["id"])]
    return watch | {
        "active": bool(watch["active"]),
        "origin_label": airports.label(watch["origin"]),
        "destination_label": airports.label(watch["destination"]),
        "recommendation": insights.recommend(
            prices,
            depart_date=date.fromisoformat(watch["depart_date"]),
            target_price=watch["target_price"],
        ).as_dict(),
    }


def get_watch(watch_id: int) -> dict | None:
    return next((watch for watch in list_watches() if watch["id"] == watch_id), None)


def create_watch(payload: dict) -> dict:
    with session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO watches
                (origin, destination, depart_date, return_date, adults, currency, target_price,
                 flex_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["origin"],
                payload["destination"],
                payload["depart_date"].isoformat(),
                payload["return_date"].isoformat() if payload.get("return_date") else None,
                payload["adults"],
                payload["currency"],
                payload.get("target_price"),
                min(payload.get("flex_days", 0), config.MAX_FLEX_DAYS),
            ),
        )
        watch_id = int(cursor.lastrowid)
    return get_watch(watch_id)


def delete_watch(watch_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    return cursor.rowcount > 0


def set_active(watch_id: int, active: bool) -> dict | None:
    with session() as conn:
        conn.execute("UPDATE watches SET active = ? WHERE id = ?", (int(active), watch_id))
    return get_watch(watch_id)


def price_history(watch_id: int) -> list[dict]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT price, currency, carrier, deep_link, for_date, checked_at
            FROM prices WHERE watch_id = ? ORDER BY checked_at, id
            """,
            (watch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_alerts(limit: int = 50) -> list[dict]:
    with session() as conn:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def _shift(request: SearchRequest, offset: int) -> SearchRequest:
    """The same itinerary moved by `offset` days, keeping the trip length intact."""
    return SearchRequest(
        origin=request.origin,
        destination=request.destination,
        depart_date=request.depart_date + timedelta(days=offset),
        return_date=request.return_date + timedelta(days=offset) if request.return_date else None,
        adults=request.adults,
        currency=request.currency,
    )


def _flex_offsets(flex_days: int) -> list[int]:
    """Day offsets to try, nearest the requested date first: 0, -1, +1, -2, +2 ..."""
    offsets = [0]
    for day in range(1, min(flex_days, config.MAX_FLEX_DAYS) + 1):
        offsets += [-day, day]
    return offsets


async def cheapest_flexible(
    provider, request: SearchRequest, flex_days: int
) -> tuple[Quote | None, date]:
    """Cheapest quote across the date window, plus the departure date that produced it.

    Dates already in the past are skipped, and a provider failure on one candidate
    date never loses a cheaper result from another.
    """
    best: Quote | None = None
    best_date = request.depart_date
    for offset in _flex_offsets(flex_days):
        candidate = _shift(request, offset)
        if candidate.depart_date < date.today():
            continue
        try:
            quote = await provider.cheapest(candidate)
        except ProviderError:
            logger.exception(
                "provider failed for %s→%s on %s",
                candidate.origin,
                candidate.destination,
                candidate.depart_date,
            )
            continue
        if quote is not None and (best is None or quote.price < best.price):
            best, best_date = quote, candidate.depart_date
    return best, best_date


async def check_watch(watch_id: int, provider_name: str = "") -> dict | None:
    """Fetch the current cheapest price for a watch, store it, and alert on a drop."""
    with session() as conn:
        row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    if row is None:
        return None

    provider = get_provider(provider_name)
    flex_days = row["flex_days"] or 0
    quote, for_date = await cheapest_flexible(provider, _search_request(row), flex_days)
    if quote is None:
        return None

    with session() as conn:
        previous = conn.execute(
            "SELECT MIN(price) AS lowest FROM prices WHERE watch_id = ?", (watch_id,)
        ).fetchone()["lowest"]
        conn.execute(
            """
            INSERT INTO prices (watch_id, price, currency, carrier, deep_link, for_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                watch_id,
                quote.price,
                quote.currency,
                quote.carrier,
                quote.deep_link,
                for_date.isoformat(),
            ),
        )

        target = row["target_price"]
        route = f"{row['origin']}→{row['destination']}"
        when = f"on {for_date}"
        if flex_days and for_date.isoformat() != row["depart_date"]:
            when = f"on {for_date} (cheapest within ±{flex_days} days)"
        message = ""
        if target is not None and quote.price <= target:
            message = (
                f"{route} {when} is {quote.currency} {quote.price:.2f}, "
                f"at or below your target of {target:.2f}"
            )
        elif previous is not None and quote.price < previous:
            message = (
                f"{route} {when} dropped to {quote.currency} {quote.price:.2f} "
                f"(previous low {previous:.2f})"
            )
    delivered: list[str] = []
    if message:
        logger.info("ALERT: %s", message)
        delivered = await notifiers.dispatch(
            f"Fare alert: {row['origin']}→{row['destination']}", message
        )
        with session() as conn:
            conn.execute(
                """
                INSERT INTO alerts (watch_id, price, currency, message, delivered_to)
                VALUES (?, ?, ?, ?, ?)
                """,
                (watch_id, quote.price, quote.currency, message, ",".join(delivered)),
            )

    return {
        "watch_id": watch_id,
        "price": quote.price,
        "currency": quote.currency,
        "carrier": quote.carrier,
        "deep_link": quote.deep_link,
        "for_date": for_date.isoformat(),
        "alerted": bool(message),
        "message": message,
        "delivered_to": delivered,
    }


async def check_all_active(provider_name: str = "") -> list[dict]:
    with session() as conn:
        ids = [row["id"] for row in conn.execute("SELECT id FROM watches WHERE active = 1")]

    results = []
    for watch_id in ids:
        try:
            result = await check_watch(watch_id, provider_name)
        except ProviderError:
            logger.exception("provider failed for watch %s", watch_id)
            continue
        if result:
            results.append(result)
    return results


async def explore(
    origin: str,
    depart_date: date,
    currency: str = "USD",
    max_price: float | None = None,
    limit: int = 10,
    provider_name: str = "",
) -> list[dict]:
    """Cheapest destinations from an origin, for when you have no fixed destination."""
    provider = get_provider(provider_name)
    quotes: list[DestinationQuote] = await provider.destinations(
        origin.upper(), depart_date, currency.upper(), limit
    )
    return [
        {
            "destination": quote.destination,
            "destination_label": airports.label(quote.destination),
            "price": round(quote.price, 2),
            "currency": quote.currency,
            "depart_date": quote.depart_date.isoformat(),
            "return_date": quote.return_date.isoformat() if quote.return_date else None,
            "deep_link": quote.deep_link,
        }
        for quote in quotes
        if max_price is None or quote.price <= max_price
    ]


VERDICT_LABELS = {"buy": "BUY", "wait": "WAIT", "watch": "WATCH"}


def digest_body() -> str:
    """One-line-per-watch summary of every watch, for the daily digest email."""
    watches = list_watches()
    if not watches:
        return "No watches yet — add a route at your tracker to start following fares."

    lines = []
    for watch in watches:
        recommendation = watch["recommendation"]
        route = f"{watch['origin_label']} → {watch['destination_label']}"
        latest = watch["latest_price"]
        if latest is None:
            lines.append(f"{route} on {watch['depart_date']}: no price checks yet")
            continue
        state = "" if watch["active"] else " [paused]"
        target = f", target {watch['target_price']:.0f}" if watch["target_price"] else ""
        lines.append(
            f"{VERDICT_LABELS.get(recommendation['verdict'], '')} {route} on "
            f"{watch['depart_date']}{state}: {watch['currency']} {latest:.0f} "
            f"(low {watch['lowest_price']:.0f}{target}) — {recommendation['reason']}"
        )
    return "\n".join(lines)


async def send_digest() -> dict:
    """Email the digest to every configured channel."""
    body = digest_body()
    delivered = await notifiers.dispatch("Flight tracker daily digest", body)
    return {"delivered_to": delivered, "body": body}
