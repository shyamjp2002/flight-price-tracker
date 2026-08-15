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
| GET | `/api/alerts` | recorded price-drop alerts, with the channels each was delivered to |
| GET | `/api/notifications` | channels that are currently configured |
| POST | `/api/notifications/test` | send a test alert to every configured channel |

An alert is recorded when the fare is at or below `target_price`, or when it undercuts the lowest
price seen so far.

## Notifications

Every alert is also pushed to whichever channels are configured; a channel is enabled purely by
setting its variables. Delivery failures are logged and never abort a price check — the alert is
stored either way.

| Channel | Variables |
| --- | --- |
| Email (SMTP) | `SMTP_HOST`, `SMTP_PORT` (default `587`; `465` uses SSL), `SMTP_USERNAME`, `SMTP_PASSWORD`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO` (comma-separated) |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Webhook | `ALERT_WEBHOOK_URL` (posts JSON `{"subject", "text"}` — works with Slack/Discord/Zapier hooks) |

Gmail needs an [app password](https://myaccount.google.com/apppasswords), not your account password.
For Telegram, create a bot with @BotFather and read your chat id from
`https://api.telegram.org/bot<token>/getUpdates`. Verify a setup with
`curl -X POST localhost:8000/api/notifications/test`.

## Deploy to Fly.io

The scheduler only polls while the API runs, so deploy it to keep watching 24/7. SQLite lives on a
persistent volume mounted at `/srv/data`.

```bash
fly launch --no-deploy --copy-config --name flight-price-tracker
fly volumes create tracker_data --size 1 --region sin
fly secrets set PRICE_PROVIDER=amadeus AMADEUS_CLIENT_ID=... AMADEUS_CLIENT_SECRET=... \
  SMTP_HOST=smtp.gmail.com SMTP_USERNAME=you@gmail.com SMTP_PASSWORD=... \
  ALERT_EMAIL_FROM=you@gmail.com ALERT_EMAIL_TO=you@gmail.com
fly deploy
```

`fly.toml` keeps one machine always running (`auto_stop_machines = false`) so scheduled checks keep
firing, and health-checks `/api/health`. Change the interval with
`fly secrets set CHECK_INTERVAL_MINUTES=15`.

## Tests and lint

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
cd frontend && npm run lint && npm run build
```

## Adding a provider

Implement `cheapest(SearchRequest) -> Quote | None` (see `app/providers/base.py`) and register it in
`app/providers/__init__.py`.
