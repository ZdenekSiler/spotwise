#!/usr/bin/env bash
# Local dev server: uvicorn with reload on :8000, local SQLite, temp session secret.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env from repo root if present.
if [ -f ../.env ]; then
  set -a; . ../.env; set +a
fi

# Fallbacks for a first run (dev only — never use these in production).
export SESSION_SECRET="${SESSION_SECRET:-dev-secret-please-change-me-0123456789abcdef}"
export ALLOWED_ORIGIN="${ALLOWED_ORIGIN:-*}"
export DB_PATH="${DB_PATH:-$SCRIPT_DIR/data/spotwise.db}"

uv sync
exec uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
