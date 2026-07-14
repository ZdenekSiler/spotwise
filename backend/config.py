"""Configuration and secret loading.

Single pattern for every secret: prefer a Docker file secret at /run/secrets/<name>
(production), then fall back to an environment variable (dev). Mirrors the reference projects.
"""

from __future__ import annotations

import os
from pathlib import Path

_SECRETS_DIR = Path("/run/secrets")


# ─── Secrets ───

def read_secret(name: str, env_fallback: str | None = None) -> str | None:
    """Read secret ``name`` from /run/secrets/<name>, else from env ``env_fallback``.

    Returns None if neither is present. Callers decide whether that is fatal.
    """
    secret_path = _SECRETS_DIR / name
    if secret_path.is_file():
        value = secret_path.read_text(encoding="utf-8").strip()
        if value:
            return value
    if env_fallback:
        value = os.environ.get(env_fallback)
        if value:
            return value.strip()
    return None


# ─── Environment ───

def is_production() -> bool:
    """Prod is anything that pins a real allowed origin (not the dev wildcard)."""
    return allowed_origin() != "*"


def allowed_origin() -> str:
    return os.environ.get("ALLOWED_ORIGIN", "*")


def allow_signup() -> bool:
    return os.environ.get("ALLOW_SIGNUP", "true").lower() != "false"


def db_path() -> str:
    return os.environ.get("DB_PATH", str(Path(__file__).parent / "data" / "spotwise.db"))


def entsoe_token() -> str | None:
    """Optional — the forecast layer degrades gracefully when absent."""
    return read_secret("spotwise_entsoe_token", "ENTSOE_API_TOKEN")
