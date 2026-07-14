# Architecture rules

Enforced invariants for Spotwise. Long-form human docs in [`docs/architecture.md`](../../docs/architecture.md).

## Code → goes in

| What | Goes in |
| --- | --- |
| App, lifespan (init_db + scheduler), auth routes, router mounts, `/health` | `backend/main.py` |
| A domain's `/api/<x>` routes | `backend/routers/<x>_api.py` |
| Pydantic models (`*In` / `*Out`) | `backend/models.py` |
| Async SQLite persistence (pure) | `backend/services/db.py` |
| Every SQL statement + schema + migrations | `backend/services/queries.py` |
| Thin external-source client | `backend/services/<source>.py` |
| Pure fusion/computation | `backend/services/{landed_cost,forecast}.py` |
| Secret reading | `backend/config.py` |
| Auth | `backend/auth.py` |

## Invariants (do not break)

1. **`services/db.py` must not import `fastapi`.** It raises `ValueError` on not-found; routers
   translate to `HTTPException`.
2. **All SQL lives in `services/queries.py`** as named constants. No inline SQL anywhere else.
3. **Source clients are thin**: transport + parse only. No persistence, no fusion, no HTTP
   exceptions. Fusion (`landed_cost`, `forecast`) is pure — data in, values out, no DB.
4. **Routers do not import each other.** Routers may import `db`, `models`, `auth`, services.
5. **Two API surfaces stay separate**: `/api/*` returns Pydantic / raises `HTTPException`
   (never a 200 error shape); static SPA served by nginx.
6. **Cache-then-serve**: routers read from SQLite; the scheduler refreshes caches. Never call
   an external API inline in a request path.
7. **Per-user isolation**: every consumption/savings query is parameterized on `user_id`.

## Add-a-source checklist

1. `services/<source>.py` thin client. 2. Cache DDL + migration + SQL constants in `queries.py`,
persistence in `db.py`. 3. Scheduled pull in `scheduler.py`. 4. Router + `docs/data-sources.md`
entry. 5. `test_<source>.py` with `respx`.
