import logging
import sqlite3
from datetime import date

from app import notifiers
from app.db import session
from app.providers import ProviderError, SearchRequest, get_provider

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
    return [dict(row) | {"active": bool(row["active"])} for row in rows]


def get_watch(watch_id: int) -> dict | None:
    return next((watch for watch in list_watches() if watch["id"] == watch_id), None)


def create_watch(payload: dict) -> dict:
    with session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO watches
                (origin, destination, depart_date, return_date, adults, currency, target_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["origin"],
                payload["destination"],
                payload["depart_date"].isoformat(),
                payload["return_date"].isoformat() if payload.get("return_date") else None,
                payload["adults"],
                payload["currency"],
                payload.get("target_price"),
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
            SELECT price, currency, carrier, deep_link, checked_at
            FROM prices WHERE watch_id = ? ORDER BY checked_at, id
            """,
            (watch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_alerts(limit: int = 50) -> list[dict]:
    with session() as conn:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


async def check_watch(watch_id: int, provider_name: str = "") -> dict | None:
    """Fetch the current cheapest price for a watch, store it, and alert on a drop."""
    with session() as conn:
        row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    if row is None:
        return None

    provider = get_provider(provider_name)
    quote = await provider.cheapest(_search_request(row))
    if quote is None:
        return None

    with session() as conn:
        previous = conn.execute(
            "SELECT MIN(price) AS lowest FROM prices WHERE watch_id = ?", (watch_id,)
        ).fetchone()["lowest"]
        conn.execute(
            """
            INSERT INTO prices (watch_id, price, currency, carrier, deep_link)
            VALUES (?, ?, ?, ?, ?)
            """,
            (watch_id, quote.price, quote.currency, quote.carrier, quote.deep_link),
        )

        target = row["target_price"]
        message = ""
        if target is not None and quote.price <= target:
            message = (
                f"{row['origin']}→{row['destination']} on {row['depart_date']} is "
                f"{quote.currency} {quote.price:.2f}, at or below your target of {target:.2f}"
            )
        elif previous is not None and quote.price < previous:
            message = (
                f"{row['origin']}→{row['destination']} on {row['depart_date']} dropped to "
                f"{quote.currency} {quote.price:.2f} (previous low {previous:.2f})"
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
