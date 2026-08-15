# Flight Price Tracker

Track flight routes, poll the cheapest fare on a schedule, and get alerted when the price drops
below your target.

- **Backend:** FastAPI + SQLite (stdlib `sqlite3`), APScheduler for recurring checks
- **Frontend:** React + TypeScript (Vite), recharts price history
- **Providers:** pluggable — `mock` (deterministic prices, no API key), `travelpayouts` (real
  fares, free token), `amadeus` (enterprise keys only)
- **Features:** flexible dates (±N days), buy-now-or-wait signal from your own history, airport
  autocomplete, daily digest email, "go anywhere" cheapest-destination search

## Quick start (Docker Compose)

One container builds the React UI and serves it from the API on port 8000, with the scheduler
running inside it:

```bash
cp .env.example .env    # fill in email/Telegram/webhook and provider settings
docker compose up -d --build
```

Open http://localhost:8000. Compose reads every variable from `.env`, restarts the container after a
reboot (`restart: unless-stopped`), and keeps watches and price history in the `tracker-data` volume.

```bash
docker compose logs -f                                    # follow checks and alerts
curl -X POST http://localhost:8000/api/notifications/test # send a test alert
curl -X POST http://localhost:8000/api/check-all          # check every watch now
docker compose down                                       # stop (volume is kept)
```

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload            # http://127.0.0.1:8000/docs

cd frontend && npm install && npm run dev          # http://localhost:5173 (proxies /api)
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRICE_PROVIDER` | `mock` | `mock`, `travelpayouts`, or `amadeus` |
| `TRAVELPAYOUTS_TOKEN` | – | free token for real fares |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | – | Amadeus enterprise credentials |
| `AMADEUS_BASE_URL` | `https://test.api.amadeus.com` | use `https://api.amadeus.com` for production |
| `CHECK_INTERVAL_MINUTES` | `60` | scheduler polling interval |
| `ENABLE_SCHEDULER` | `1` | set `0` to disable background checks |
| `MAX_FLEX_DAYS` | `3` | cap on a watch's flexible-date window |
| `DAILY_DIGEST` | `0` | set `1` to email one summary a day |
| `DIGEST_HOUR_UTC` | `7` | hour (UTC) the digest is sent |
| `DATABASE_PATH` | `./data/flights.db` | SQLite file location |

Real prices need a Travelpayouts token (free, no card): sign up and grab it from
https://www.travelpayouts.com/programs/100/tools/api, then run with
`PRICE_PROVIDER=travelpayouts`. Amadeus' self-service portal was decommissioned on 17 July 2026,
so the `amadeus` provider now only works with enterprise credentials.

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
| GET | `/api/airports?q=` | airport search by IATA code, city, or name |
| GET | `/api/explore?origin=&depart_date=` | cheapest destinations from one airport |
| GET | `/api/digest` | preview the daily digest |
| POST | `/api/digest/send` | send the digest now |
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

Implement `cheapest(SearchRequest) -> Quote | None` and
`destinations(origin, depart_date, currency, limit) -> list[DestinationQuote]`
(see `app/providers/base.py`), then register the class in `PROVIDERS` in
`app/providers/__init__.py`.
