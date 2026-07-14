#!/usr/bin/env bash
# Restore a backup into the running backend container: scripts/restore.sh <file>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

FILE="${1:-}"
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "usage: scripts/restore.sh <backup.db>"; exit 1; }
cat "$FILE" | docker compose exec -T backend sh -c "cat > /tmp/r.db && sqlite3 /data/spotwise.db '.restore /tmp/r.db'"
echo "restored from $FILE"
