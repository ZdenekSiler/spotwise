---
name: deploy
description: Deploy Spotwise to dev (local Docker) or prod (Hetzner VPS). Usage: /deploy dev or /deploy prod [commit message].
argument-hint: dev | prod [commit message]
---

# /deploy

Wraps the `Makefile` deploy flow. See [`docs/deployment.md`](../../../docs/deployment.md).

## /deploy dev

1. `make test` — must be green.
2. `make dev` — `docker compose up --build` (base file). Backend internal, frontend nginx on
   `${FRONTEND_PORT:-80}`, no TLS.
3. Health-check `http://localhost:${FRONTEND_PORT:-80}` and the backend `/health`.

## /deploy prod

1. Ensure a clean tree on a feature branch; run `make test`.
2. If a commit message was given, commit (Conventional Commits) and push.
3. `make deploy` — over SSH: backup DB → `git pull --ff-only` → prod compose up
   (`-f docker-compose.yml -f docker-compose.prod.yml`, external `zdenovo_public` network,
   Docker secrets) → curl health check on `https://spotwise.${DOMAIN}`.
4. On failure, report the failing step; `make logs` for diagnosis. Do not retry blindly.

## Guardrails

Never deploy prod with failing tests or uncommitted changes. Secrets come from `secrets/` files
on the server, never the repo.
