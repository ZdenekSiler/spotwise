#!/usr/bin/env bash
# Online SQLite backup out of the running backend container. Keeps the 30 newest.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

mkdir -p backups
OUT="backups/spotwise-$(date +%Y-%m-%d-%H%M%S).db"
docker compose exec -T backend sh -c "sqlite3 /data/spotwise.db '.backup /tmp/b.db' && cat /tmp/b.db" > "$OUT"
echo "backup -> $OUT"
ls -1t backups/spotwise-*.db | tail -n +31 | xargs -r rm --
