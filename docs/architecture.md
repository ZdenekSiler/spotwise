# Architecture

Authoritative module map and import rules. See [`../DESIGN.md`](../DESIGN.md) for the product
overview and [`../.claude/rules/architecture.md`](../.claude/rules/architecture.md) for the
enforced invariants (this file is the human-readable long form).

## Code → goes in

| What | Goes in |
| --- | --- |
| FastAPI app, lifespan (init_db + scheduler), auth routes, router mounts, `/health` | `backend/main.py` |
| A domain's HTTP routes (`/api/<x>`) | `backend/routers/<x>_api.py` |
| Pydantic domain models (`*In` / `*Out`) | `backend/models.py` |
| SQLite persistence (async, pure — no `fastapi` import) | `backend/services/db.py` |
| Every SQL statement (named constant) + `DDL_CREATE_SCHEMA` + `_MIGRATIONS` | `backend/services/queries.py` |
| A thin external-source client | `backend/services/<source>.py` |
| Pure fusion / computation (landed cost, forecast direction, savings) | `backend/services/{landed_cost,forecast}.py` |
| Background jobs | `backend/services/scheduler.py` |
| Secret reading | `backend/config.py` (`read_secret`) |
| Auth (hashing, cookie, `current_user_id` dep) | `backend/auth.py` |

## Import rules

- `services/db.py` imports nothing internal except `queries`; **must not import `fastapi`**.
  It raises `ValueError` on not-found — routers translate to `HTTPException`.
- All SQL lives in `services/queries.py`; `db.py` contains no inline SQL.
- Source clients (`ote`, `entsoe`, `weather`, `cnb`) do not import routers.
- Fusion modules (`landed_cost`, `forecast`) are pure: they take data in, return values out;
  they do not touch `db.py` directly — routers fetch and pass data in.
- Routers may import `db`, `models`, `auth`, and services. Routers do not import each other.

## API surfaces

Two strictly separated surfaces: `/api/*` returns Pydantic / raises `HTTPException` (never a
200 error shape); static SPA is served by nginx. Endpoint tables:

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | public | liveness |
| POST | `/auth/signup`, `/auth/login`, `/auth/logout` | public | session |
| GET | `/api/prices` | public | spot series + landed-cost tiles |
| GET | `/api/tariffs` | public | DSO tariffs + supplier price lists |
| POST | `/api/consumption` | user | upload 15-min CSV |
| GET | `/api/consumption` | user | user's series |
| GET | `/api/savings` | user | personalized savings + backtested ranking |
| GET | `/api/forecast` | public | day+2/+3 directional forecast |

## Add-a-source checklist

1. Add a thin client `services/<source>.py` (httpx + a stdlib parser; no business logic, no heavy libs).
2. Add cache table DDL + migration guard + SQL constants in `queries.py`; persistence in `db.py`.
3. Wire a scheduled pull in `services/scheduler.py` if the source has a publish cadence.
4. Expose via a router; document access/cadence/ethics in `docs/data-sources.md`.
5. Add `test_<source>.py` mocking HTTP with `respx`.
