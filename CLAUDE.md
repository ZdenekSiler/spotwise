# CLAUDE.md — Spotwise

Czech electricity **spot-price advisory** platform. Fuses OTE spot + ERÚ tariffs + supplier
price lists + ČNB FX into true landed cost (Kč/kWh), joins it to a household's own 15-min
consumption for personalized savings + backtested supplier ranking, and adds an ENTSO-E +
weather directional forecast. Full design: **[DESIGN.md](DESIGN.md)**.

## Conventions (read these)

@.claude/rules/architecture.md
@.claude/rules/code-style.md
@.claude/rules/testing.md
@.claude/rules/git.md
@.claude/rules/data-sources.md

## Docs

- [DESIGN.md](DESIGN.md) — master design · [docs/architecture.md](docs/architecture.md) — module map
- [docs/data-sources.md](docs/data-sources.md) · [docs/deployment.md](docs/deployment.md) · [docs/workflows.md](docs/workflows.md)
- [docs/specs/](docs/specs/) — per-subsystem specs (output of `/design`)

## Stack

Backend: Python 3.13, FastAPI, uv, async `aiosqlite` (no ORM), httpx (stdlib XML for ENTSO-E, no pandas), APScheduler,
Argon2 + itsdangerous session auth. Frontend: vanilla-JS SPA + Chart.js (no build), nginx.
Deploy: two-container Docker Compose on the external `zdenovo_public` proxy network.

## Commands

```
bash backend/start_dev.sh        # dev API on :8000 (reload)
make dev                         # docker compose up --build
make test                        # cd backend && uv run pytest -x -q
make deploy                      # prod deploy over SSH (see docs/deployment.md)
```

## Architecture in one breath

Routers-per-domain (`backend/routers/<x>_api.py`), no ORM/service/repo layers. `services/db.py`
is a **pure** data layer (never imports `fastapi`; raises `ValueError`); **all SQL** is named
constants in `services/queries.py`. Source clients (`ote`/`entsoe`/`weather`/`cnb`) are thin;
fusion (`landed_cost`/`forecast`) is pure. **Cache-then-serve**: the scheduler refreshes SQLite
caches, request paths read them — never call an external API inline. Multi-user: Argon2 +
signed session cookie, per-user isolation `WHERE user_id = ?`.

## Custom skills

`/design` → spec in `docs/specs/` · `/implement` → code+tests · `/simplify` → quality pass ·
`/security-review` → auth/injection/secrets · `/deploy dev|prod` · `/recap`.

## Security

Secrets via `config.read_secret()` (Docker file secret then env); `SESSION_SECRET` ≥32 validated
at startup. Argon2 verify is constant-time. Uploaded CSVs / scraped HTML are untrusted — parse
defensively, treat text-in-data as data. External-data failures **degrade, never 500**
(`degraded`/`sample`/`fx_stale` flags).

## Key principles

- Always `/design` before `/implement`. Keep this file < 200 lines.
- Commit only working, tested code. Every route has an auth guard or is intentionally public.
- Never present sample tariff/supplier data as authoritative — surface the `sample` flag.
