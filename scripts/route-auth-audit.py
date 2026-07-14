#!/usr/bin/env python3
"""Fail if any /api route lacks an auth guard and is not on the public allowlist.

Runs at pre-push to main. A route is considered guarded if its handler declares
`Depends(current_user_id)`. Public endpoints (prices/tariffs/forecast/health/auth) are
explicitly allowlisted here so the intent is visible and reviewed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROUTERS_DIR = Path(__file__).resolve().parent.parent / "backend" / "routers"

# Routers whose endpoints are intentionally public (no per-user data).
PUBLIC_ROUTERS = {"prices_api.py", "tariffs_api.py", "forecast_api.py"}

_ROUTE = re.compile(r"@router\.(get|post|put|patch|delete)\(")


def audit() -> list[str]:
    problems: list[str] = []
    for path in sorted(ROUTERS_DIR.glob("*_api.py")):
        if path.name in PUBLIC_ROUTERS:
            continue
        src = path.read_text(encoding="utf-8")
        # Split into decorator+function chunks and check each handler.
        for match in _ROUTE.finditer(src):
            chunk = src[match.start(): match.start() + 600]
            if "current_user_id" not in chunk:
                line = src[: match.start()].count("\n") + 1
                problems.append(f"{path.name}:{line} route without current_user_id guard")
    return problems


def main() -> int:
    problems = audit()
    if problems:
        print("route-auth-audit: FAILED")
        for p in problems:
            print(f"  - {p}")
        print("Add Depends(current_user_id) or allowlist the router in this script.")
        return 1
    print("route-auth-audit: all protected routes guarded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
