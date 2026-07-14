# Spotwise

Know when to use power — and which supplier is actually cheapest **for you**.

Spotwise is a Czech electricity spot-price advisory platform. The raw day-ahead spot price is
only ~⅓ of a real bill, so Spotwise **fuses the sources nobody combines**:

- **OTE** day-ahead/intraday spot + **ERÚ** distribution tariffs + **supplier** price lists +
  **ČNB** EUR/CZK → true **landed cost** in Kč/kWh.
- Your own **15-min smart-meter** consumption → **personalized savings** and a **backtested
  supplier ranking** ("for your usage, switching saves 2 400 Kč/yr").
- **ENTSO-E** generation/load + **Open-Meteo** weather → a **directional forecast** for
  day+2/day+3, beyond OTE's horizon.

Design: **[DESIGN.md](DESIGN.md)**. Conventions: **[CLAUDE.md](CLAUDE.md)**.

## Structure

```
spotwise/
├── DESIGN.md CLAUDE.md README.md
├── docs/               architecture, data-sources, deployment, workflows, specs/
├── .claude/            rules/ + skills/ (design, implement, simplify, security-review, deploy, recap)
├── backend/            FastAPI (uv), routers/, services/, seed/, tests/
├── frontend/           vanilla-JS SPA + Chart.js, served by nginx
└── Makefile docker-compose*.yml Caddyfile
```

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.13, FastAPI, uv, async `aiosqlite` (no ORM) |
| External data | httpx clients (OTE, ČNB, Open-Meteo, ENTSO-E — stdlib XML, no pandas) |
| Jobs | APScheduler (OTE ~13:00, ČNB daily, ENTSO-E/weather) |
| Auth | Argon2id + signed session cookie, per-user SQL isolation |
| Frontend | Vanilla JS, Chart.js, CSS design tokens, nginx (no build step) |
| Deploy | Docker Compose ×2 on external `zdenovo_public` proxy network |

## Getting started

```bash
cp .env.example .env          # fill SESSION_SECRET (and ENTSOE_API_TOKEN if you have one)
cd backend && uv sync
bash start_dev.sh             # API on http://localhost:8000  (/api/docs in dev)
# or, full stack:
make dev                      # http://localhost
make test                     # uv run pytest -x -q
```

## API (summary)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | – | liveness |
| POST | `/auth/{signup,login,logout}` | – | session |
| GET | `/api/prices` | – | spot series + landed-cost tiles |
| GET | `/api/tariffs` | – | DSO tariffs + supplier price lists |
| POST/GET | `/api/consumption` | user | upload / read 15-min series |
| GET | `/api/savings` | user | personalized savings + backtested ranking |
| GET | `/api/forecast` | – | day+2/+3 directional forecast |

## Status

MVP scaffold. ERÚ tariffs and supplier price lists ship as **sample** seed data; live scraping
is a documented follow-up. ENTSO-E forecasting needs a free token and degrades to
day-ahead-only without one. See [docs/data-sources.md](docs/data-sources.md).

## License

MIT.
