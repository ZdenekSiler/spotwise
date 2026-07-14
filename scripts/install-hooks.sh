#!/usr/bin/env bash
# Symlink the source-controlled git hooks into .git/hooks. Run once after cloning.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$ROOT/.git" ]; then
  echo "not a git repo yet — run 'git init' first"; exit 1
fi

for hook in pre-commit pre-push; do
  ln -sf "../../scripts/hooks/$hook" "$ROOT/.git/hooks/$hook"
  chmod +x "$SCRIPT_DIR/hooks/$hook"
  echo "installed $hook"
done
