# Spotwise — Design

> Master design document. Authoritative overview of *what* Spotwise is and *how* it is built.
> Detailed per-subsystem designs live in [`docs/specs/`](docs/specs/). Conventions live in
> [`.claude/rules/`](.claude/rules/) and [`docs/architecture.md`](docs/architecture.md).

## 1. Product thesis

Spotwise helps Czech households on (or considering) dynamic **spot** electricity tariffs
answer one question: *"given the market **and my own consumption**, when should I use power,
and which supplier is actually cheapest for me?"*

The raw day-ahead spot price is roughly **one third** of a final bill and is meaningless on
its own. Spotwise's value is in **fusing sources nobody combines today**:

| Combination | Produces |
| --- | --- |
| OTE spot + ERÚ tariffs + supplier price list + ČNB FX | **True landed cost** in Kč/kWh, per supplier |
| Landed cost + household's own 15-min consumption | **Personalized savings** ("*for your usage, switching saves 2 400 Kč/yr*") |
| ENTSO-E generation/load + Open-Meteo weather | **Directional forecast** for day+2 / day+3 (beyond OTE's horizon) |
| Historical negative-price stats + shiftable-load profile | Quantified **"free electricity" capture** opportunity |
| All supplier price lists + full historical spot series + user's curve | **Backtested supplier ranking** |

## 2. Data sources

Free, mostly key-less; one email-registered token (ENTSO-E). See
[`docs/data-sources.md`](docs/data-sources.md) for access, cadence, and scraping ethics.

| Source | Gives | Access | Granularity | Client |
| --- | --- | --- | --- | --- |
| **OTE** (day-ahead + intraday) | CZ spot price, core commodity | Free REST (spotovaelektrina.cz wraps OTE) / raw OTE files | 15-min, published ~13:00 | `services/ote.py` |
| **ENTSO-E** Transparency | Load, generation-by-fuel (DE/AT solar+wind), neighbor prices | Free REST, email token; raw XML via `httpx` (no `entsoe-py`/pandas) | Hourly/15-min | `services/entsoe.py` |
| **Open-Meteo** | Solar irradiance + wind forecast | Free, no key | Hourly, days out | `services/weather.py` |
| **ČNB** | Daily EUR/CZK (OTE settles in EUR) | Free daily publication | Daily | `services/cnb.py` |
| **ERÚ** | Regulated DSO distribution tariffs (ČEZ/EGD/PRE) | Published decisions (scrape) | Annual | `seed/dso_tariffs.json` |
| **Supplier price lists** (ceníky) | Markup over spot + monthly fee | Scrape each supplier | Irregular | `seed/suppliers.json` |
| **Smart-meter export** | User's own 15-min consumption | Distributor portal / manual upload | 15-min | `routers/consumption_api.py` |

## 3. Architecture

Synthesis of the two reference projects: **zdenovo** backend structure (uv + FastAPI,
routers-per-domain, no ORM/service/repo layers, `read_secret()`, APScheduler, idempotent
`init_db()` migrations, `*In`/`*Out` Pydantic + `HTTPException`) + **invoice_app** data/auth
layer (async `aiosqlite`, SQL as named constants in `queries.py`, multi-user Argon2
session-cookie auth with per-user SQL isolation) + **invoice_app** vanilla-JS SPA frontend and
two-container Docker Compose deploy on the external `zdenovo_public` proxy network.

```
                        ┌────────── APScheduler jobs ──────────┐
                        │  OTE ~13:00 · ČNB daily · ENTSO-E/WX  │
                        ▼                                        │
  External sources → services/{ote,entsoe,weather,cnb}.py → SQLite cache
        (httpx + stdlib parsers, thin clients, cache-then-serve)   │
                                                                   ▼
  services/landed_cost.py  ── fuse spot+tariff+supplier+fx ──►  Kč/kWh
  services/forecast.py     ── residual-load + weather      ──►  direction
                                                                   │
  routers/{prices,tariffs,consumption,savings,forecast}_api.py  (/api/*)
        │  auth.py (Argon2 + signed session cookie, WHERE user_id=?)
        ▼
  frontend SPA (vanilla JS + Chart.js, nginx) ── dashboard / upload / savings / forecast
```

**Layering invariants** (enforced, see `.claude/rules/architecture.md`):
`services/db.py` is a pure data layer and must **not** import `fastapi` (raises `ValueError`
on not-found; routers translate to `HTTPException`). Every SQL statement is a named constant
in `services/queries.py`. Source clients are thin wrappers; fusion logic (`landed_cost`,
`forecast`) is pure and independently unit-tested.

## 4. Database schema (SQLite)

| Table | Key columns | Notes |
| --- | --- | --- |
| `users` | `id`, `email` UNIQUE, `password_hash`, `created_at` | Argon2id hash |
| `spot_prices` | `ts`, `zone`, `price_eur_mwh` | PK (`ts`,`zone`); 15-min day-ahead + intraday |
| `fx_rates` | `date` PK, `eur_czk` | ČNB daily |
| `dso_tariffs` | `dso`, `component`, `czk_per_kwh`, `czk_per_month` | Loaded from seed if empty |
| `suppliers` | `id`, `name`, `markup_czk_mwh`, `monthly_fee_czk`, `product` | Loaded from seed if empty |
| `consumption` | `user_id`, `ts`, `kwh` | PK (`user_id`,`ts`); per-user isolated |
| `forecasts` | `target_date`, `zone`, `direction`, `confidence`, `basis` | day+2/+3 directional |
| `entsoe_cache` / `weather_cache` | `key`, `payload`, `fetched_at` | raw cache-then-serve |

Migrations are idempotent `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` guards inside
`init_db()` — no Alembic (zdenovo convention).

## 5. Feature areas → data flows

1. **Landed cost & day-ahead** (`prices_api`, `landed_cost.py`) — public. Spot series +
   fused Kč/kWh tiles per supplier. Foundation everything sits on.
2. **Accounts & consumption** (`auth.py`, `consumption_api`) — protected. Signup/login,
   smart-meter CSV upload (15-min), per-user isolation.
3. **Personalized savings & backtest** (`savings_api`, `landed_cost.py`) — protected. Runs a
   year of real spot through every supplier's fee structure against the user's own curve →
   ranked "you'd have paid X at A, Y at B" + negative-price capture estimate.
4. **Forecasting** (`forecast_api`, `forecast.py`, `entsoe.py`, `weather.py`) — public.
   Day+2/+3 directional signal from DE residual load + weather. Degrades to day-ahead-only if
   `ENTSOE_API_TOKEN` is absent.
5. **Dashboard** (frontend) — ties it together: live chart, tiles, upload, ranking, forecast.

## 6. MVP scope

**Full personalized platform**: all five feature areas. ERÚ tariffs and supplier price lists
ship as **seed JSON marked "sample"**; live scraping is a documented follow-up
([`docs/specs/`](docs/specs/) + `data-sources.md`). ENTSO-E forecasting is behind the optional
token and degrades gracefully.

## 7. Runtime footprint (deployment target)

Spotwise is sized to run comfortably on a **low-CPU shared-vCPU host (Hetzner CX-class)**. This
is a first-class design constraint, not an afterthought — it drives concrete choices:

- **SQLite, not Postgres.** No separate DB process; the whole store is one file.
- **Single uvicorn worker** (`--workers 1`). With SQLite, extra workers add write-lock
  contention, not throughput. Concurrency comes from async I/O within the one process.
- **Cache-then-serve.** External fetches happen a few times a day in the scheduler; request
  paths only read SQLite — no external I/O or fusion under user load.
- **No heavy libraries in the hot path.** ENTSO-E is parsed with the stdlib (`xml.etree`), not
  `entsoe-py` → avoids pandas + numpy (~120 MB resident + slow cold import). Prefer the stdlib
  before adding a dependency; see [`docs/data-sources.md`](docs/data-sources.md).
- **Argon2 tuned to the OWASP minimum** (19 MiB, `time_cost=2`, `parallelism=1`) rather than the
  library's many-core default (64 MiB, `parallelism=4`), so a login burst doesn't stall the
  event loop on 2 shared vCPUs — still within OWASP guidance.
- **Lean container.** `python:3.13-slim` base, `uv sync --no-dev` (dev/security tooling never
  ships), bytecode precompiled at build for cheaper cold starts; nginx on `alpine`; no Node/
  build step for the frontend (vanilla JS served static).

## 8. Subsystem specs

- [`docs/specs/landed-cost.md`](docs/specs/landed-cost.md)
- [`docs/specs/consumption-and-accounts.md`](docs/specs/consumption-and-accounts.md)
- [`docs/specs/savings-and-backtest.md`](docs/specs/savings-and-backtest.md)
- [`docs/specs/forecasting.md`](docs/specs/forecasting.md)
