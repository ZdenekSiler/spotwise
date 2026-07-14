"""All SQL for Spotwise as named constants.

No SQL lives anywhere else. Sections mirror the tables and the functions in db.py.
Schema is DDL_CREATE_SCHEMA; additive migrations go in _MIGRATIONS (idempotent guards run by
db.init_db()).
"""

from __future__ import annotations

# ─── Schema ───

DDL_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    current_supplier INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS spot_prices (
    ts            TEXT NOT NULL,
    zone          TEXT NOT NULL DEFAULT 'CZ',
    price_eur_mwh REAL NOT NULL,
    PRIMARY KEY (ts, zone)
);

CREATE TABLE IF NOT EXISTS fx_rates (
    date    TEXT PRIMARY KEY,
    eur_czk REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dso_tariffs (
    dso           TEXT NOT NULL,
    component     TEXT NOT NULL,
    czk_per_kwh   REAL NOT NULL DEFAULT 0,
    czk_per_month REAL NOT NULL DEFAULT 0,
    sample        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (dso, component)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    product         TEXT,
    markup_czk_mwh  REAL NOT NULL DEFAULT 0,
    monthly_fee_czk REAL NOT NULL DEFAULT 0,
    sample          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS consumption (
    user_id INTEGER NOT NULL,
    ts      TEXT NOT NULL,
    kwh     REAL NOT NULL,
    PRIMARY KEY (user_id, ts)
);

CREATE TABLE IF NOT EXISTS forecasts (
    target_date TEXT NOT NULL,
    zone        TEXT NOT NULL DEFAULT 'CZ',
    direction   TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 0,
    basis       TEXT,
    PRIMARY KEY (target_date, zone)
);

CREATE TABLE IF NOT EXISTS source_cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Additive, idempotent migrations: (table, column, column_def). db.init_db() adds each only if
# the column is missing (PRAGMA table_info guard). Never rewrite existing rows here.
_MIGRATIONS: list[tuple[str, str, str]] = [
    # ("users", "example_col", "TEXT"),
]

# ─── users ───

USER_INSERT = "INSERT INTO users (email, password_hash) VALUES (?, ?)"
USER_BY_EMAIL = "SELECT id, email, password_hash, current_supplier FROM users WHERE email = ?"
USER_BY_ID = "SELECT id, email, current_supplier FROM users WHERE id = ?"
USER_SET_SUPPLIER = "UPDATE users SET current_supplier = ? WHERE id = ?"

# ─── spot_prices ───

SPOT_UPSERT = (
    "INSERT INTO spot_prices (ts, zone, price_eur_mwh) VALUES (?, ?, ?) "
    "ON CONFLICT(ts, zone) DO UPDATE SET price_eur_mwh = excluded.price_eur_mwh"
)
SPOT_RANGE = (
    "SELECT ts, zone, price_eur_mwh FROM spot_prices "
    "WHERE zone = ? AND ts >= ? AND ts < ? ORDER BY ts"
)
SPOT_ALL_FOR_ZONE = (
    "SELECT ts, zone, price_eur_mwh FROM spot_prices WHERE zone = ? ORDER BY ts"
)

# ─── fx_rates ───

FX_UPSERT = (
    "INSERT INTO fx_rates (date, eur_czk) VALUES (?, ?) "
    "ON CONFLICT(date) DO UPDATE SET eur_czk = excluded.eur_czk"
)
FX_ON_OR_BEFORE = "SELECT date, eur_czk FROM fx_rates WHERE date <= ? ORDER BY date DESC LIMIT 1"
FX_LATEST = "SELECT date, eur_czk FROM fx_rates ORDER BY date DESC LIMIT 1"

# ─── dso_tariffs ───

DSO_INSERT = (
    "INSERT OR REPLACE INTO dso_tariffs (dso, component, czk_per_kwh, czk_per_month, sample) "
    "VALUES (?, ?, ?, ?, ?)"
)
DSO_BY_DSO = (
    "SELECT dso, component, czk_per_kwh, czk_per_month, sample FROM dso_tariffs WHERE dso = ?"
)
DSO_ALL = "SELECT dso, component, czk_per_kwh, czk_per_month, sample FROM dso_tariffs ORDER BY dso"
DSO_COUNT = "SELECT COUNT(*) AS n FROM dso_tariffs"

# ─── suppliers ───

SUPPLIER_INSERT = (
    "INSERT OR REPLACE INTO suppliers "
    "(id, name, product, markup_czk_mwh, monthly_fee_czk, sample) VALUES (?, ?, ?, ?, ?, ?)"
)
SUPPLIER_BY_ID = (
    "SELECT id, name, product, markup_czk_mwh, monthly_fee_czk, sample FROM suppliers WHERE id = ?"
)
SUPPLIER_ALL = (
    "SELECT id, name, product, markup_czk_mwh, monthly_fee_czk, sample FROM suppliers ORDER BY id"
)
SUPPLIER_COUNT = "SELECT COUNT(*) AS n FROM suppliers"

# ─── consumption (per-user isolated: every statement is parameterized on user_id) ───

CONSUMPTION_UPSERT = (
    "INSERT INTO consumption (user_id, ts, kwh) VALUES (?, ?, ?) "
    "ON CONFLICT(user_id, ts) DO UPDATE SET kwh = excluded.kwh"
)
CONSUMPTION_RANGE = (
    "SELECT ts, kwh FROM consumption WHERE user_id = ? AND ts >= ? AND ts < ? ORDER BY ts"
)
CONSUMPTION_ALL = "SELECT ts, kwh FROM consumption WHERE user_id = ? ORDER BY ts"
CONSUMPTION_COUNT = "SELECT COUNT(*) AS n FROM consumption WHERE user_id = ?"

# ─── forecasts ───

FORECAST_UPSERT = (
    "INSERT INTO forecasts (target_date, zone, direction, confidence, basis) VALUES (?, ?, ?, ?, ?) "
    "ON CONFLICT(target_date, zone) DO UPDATE SET "
    "direction = excluded.direction, confidence = excluded.confidence, basis = excluded.basis"
)
FORECAST_UPCOMING = (
    "SELECT target_date, zone, direction, confidence, basis FROM forecasts "
    "WHERE zone = ? AND target_date >= ? ORDER BY target_date LIMIT ?"
)

# ─── source_cache ───

CACHE_UPSERT = (
    "INSERT INTO source_cache (key, payload, fetched_at) VALUES (?, ?, datetime('now')) "
    "ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, fetched_at = datetime('now')"
)
CACHE_GET = "SELECT payload, fetched_at FROM source_cache WHERE key = ?"
