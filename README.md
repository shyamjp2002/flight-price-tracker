# Flight Price Tracker

Track flight routes, poll the cheapest fare on a schedule, and get alerted when the price drops
below your target.

- **Backend:** FastAPI + SQLite (stdlib `sqlite3`), APScheduler for recurring checks
- **Frontend:** React + TypeScript (Vite), recharts price history
- **Providers:** pluggable — `mock` (deterministic prices, no API key) and `amadeus`
  (Flight Offers Search)

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload            # http://127.0.0.1:8000/docs

cd frontend && npm install && npm run dev          # http://localhost:5173 (proxies /api)
```

With Docker (frontend is built and served by the API on port 8000):

```bash
docker compose up --build
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRICE_PROVIDER` | `mock` | `mock` or `amadeus` |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | – | Amadeus self-service credentials |
| `AMADEUS_BASE_URL` | `https://test.api.amadeus.com` | use `https://api.amadeus.com` for production |
| `CHECK_INTERVAL_MINUTES` | `60` | scheduler polling interval |
| `ENABLE_SCHEDULER` | `1` | set `0` to disable background checks |
| `DATABASE_PATH` | `./data/flights.db` | SQLite file location |

Real prices need an Amadeus key (free self-service tier): create an app at
https://developers.amadeus.com/my-apps, then run with `PRICE_PROVIDER=amadeus`.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | status and active provider |
| GET | `/api/watches` | watches with latest price, lowest price, check count |
| POST | `/api/watches` | create a watch |
| DELETE | `/api/watches/{id}` | delete a watch and its history |
| POST | `/api/watches/{id}/active?active=` | pause or resume a watch |
| GET | `/api/watches/{id}/prices` | price history |
| POST | `/api/watches/{id}/check` | check one watch now |
| POST | `/api/check-all` | check every active watch |
| GET | `/api/alerts` | recorded price-drop alerts |

An alert is recorded when the fare is at or below `target_price`, or when it undercuts the lowest
price seen so far.

## Tests and lint

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
cd frontend && npm run lint && npm run build
```

## Adding a provider

Implement `cheapest(SearchRequest) -> Quote | None` (see `app/providers/base.py`) and register it in
`app/providers/__init__.py`.
