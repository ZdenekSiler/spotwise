# Deployment

Model mirrors `invoice_app`: two app containers (backend + frontend) on a Hetzner VPS, TLS
terminated by the shared upstream **`zdenovo`** edge proxy. All ops go through the `Makefile`.

## Local dev

- `bash backend/start_dev.sh` — uvicorn `--reload` on :8000, local `data/spotwise.db`, temp
  `SESSION_SECRET`. Frontend opened directly or via `make dev`.
- `make dev` — `docker compose up --build` (base file): backend (internal) + frontend nginx on
  `${FRONTEND_PORT:-80}`. No TLS.
- `make test` — `cd backend && uv run pytest -x -q`.

## Production

`make deploy` (over SSH): backup DB → `git pull --ff-only` → `docker compose -f
docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans` → curl health.

The prod override:
- Joins the **external** `zdenovo_public` network (the umbrella `zdenovo` stack owns the edge
  proxy + Let's Encrypt); `ports: !reset []` so nothing is published directly.
- Network aliases `spotwise-backend` / `spotwise-frontend` (the edge proxy routes
  `spotwise.${DOMAIN}` → `spotwise-frontend`).
- `SESSION_SECRET` via Docker **file secret** `spotwise_session_secret` (`./secrets/…`,
  chmod 600, gitignored); `ENTSOE_API_TOKEN` via secret/env.
- `ALLOWED_ORIGIN` / `APP_URL = https://spotwise.${DOMAIN}`, `ALLOW_SIGNUP` toggle,
  `LOG_LEVEL=warning`, `/api/docs` disabled in prod.

`Caddyfile` is present for the standalone case (`{$DOMAIN} { reverse_proxy frontend:80 }`) but
prod delegates TLS to the upstream stack.

## Data & backups

SQLite lives on the named volume `spotwise_data:/data`. `make backup` runs an online sqlite
`.backup` out of the container into `backups/spotwise-<date>.db` (keeps 30 newest);
`make restore FILE=…` restores.

## Secrets

Never commit `.env` or `secrets/`. `SESSION_SECRET` ≥32 chars is validated at startup
(process exits if missing in prod). Generate with `python -c "import secrets;
print(secrets.token_urlsafe(48))"`.
