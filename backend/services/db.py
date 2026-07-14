"""Async SQLite persistence — the pure data layer.

Invariants: this module MUST NOT import fastapi. It raises ValueError on not-found; routers
translate that to HTTPException. It contains no inline SQL — every statement is a named
constant in queries.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

import config
from services import queries


# ─── Connection & schema ───

def _path() -> str:
    return config.db_path()


async def _connect() -> aiosqlite.Connection:
    Path(_path()).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(_path())
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def init_db() -> None:
    """Create schema, run idempotent migrations, seed config tables if empty."""
    conn = await _connect()
    try:
        await conn.executescript(queries.DDL_CREATE_SCHEMA)
        await _run_migrations(conn)
        await conn.commit()
    finally:
        await conn.close()
    await _seed_if_empty()


async def _run_migrations(conn: aiosqlite.Connection) -> None:
    for table, column, coldef in queries._MIGRATIONS:
        cur = await conn.execute(f"PRAGMA table_info({table})")
        cols = {row["name"] for row in await cur.fetchall()}
        if column not in cols:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")


# ─── Seed (DSO tariffs + suppliers ship as sample JSON, loaded only when empty) ───

_SEED_DIR = Path(__file__).parent.parent / "seed"


async def _seed_if_empty() -> None:
    conn = await _connect()
    try:
        if (await _scalar(conn, queries.DSO_COUNT)) == 0:
            for row in _load_seed("dso_tariffs.json"):
                await conn.execute(
                    queries.DSO_INSERT,
                    (row["dso"], row["component"], row.get("czk_per_kwh", 0),
                     row.get("czk_per_month", 0), int(row.get("sample", 1))),
                )
        if (await _scalar(conn, queries.SUPPLIER_COUNT)) == 0:
            for row in _load_seed("suppliers.json"):
                await conn.execute(
                    queries.SUPPLIER_INSERT,
                    (row["id"], row["name"], row.get("product"), row.get("markup_czk_mwh", 0),
                     row.get("monthly_fee_czk", 0), int(row.get("sample", 1))),
                )
        await conn.commit()
    finally:
        await conn.close()


def _load_seed(name: str) -> list[dict[str, Any]]:
    path = _SEED_DIR / name
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


async def _scalar(conn: aiosqlite.Connection, sql: str, params: tuple = ()) -> Any:
    cur = await conn.execute(sql, params)
    row = await cur.fetchone()
    return row[0] if row else None


# ─── users ───

async def create_user(email: str, password_hash: str) -> int:
    conn = await _connect()
    try:
        try:
            cur = await conn.execute(queries.USER_INSERT, (email, password_hash))
        except aiosqlite.IntegrityError as exc:
            raise ValueError("email already registered") from exc
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    return await _fetch_one(queries.USER_BY_EMAIL, (email,))


async def get_user(user_id: int) -> dict[str, Any]:
    row = await _fetch_one(queries.USER_BY_ID, (user_id,))
    if row is None:
        raise ValueError("user not found")
    return row


async def set_current_supplier(user_id: int, supplier_id: int) -> None:
    await _execute(queries.USER_SET_SUPPLIER, (supplier_id, user_id))


# ─── spot_prices ───

async def upsert_spot_prices(rows: list[tuple[str, str, float]]) -> None:
    await _execute_many(queries.SPOT_UPSERT, rows)


async def spot_range(zone: str, start: str, end: str) -> list[dict[str, Any]]:
    return await _fetch_all(queries.SPOT_RANGE, (zone, start, end))


async def spot_all(zone: str) -> list[dict[str, Any]]:
    return await _fetch_all(queries.SPOT_ALL_FOR_ZONE, (zone,))


# ─── fx_rates ───

async def upsert_fx(date: str, eur_czk: float) -> None:
    await _execute(queries.FX_UPSERT, (date, eur_czk))


async def fx_on_or_before(date: str) -> dict[str, Any] | None:
    return await _fetch_one(queries.FX_ON_OR_BEFORE, (date,))


# ─── dso_tariffs & suppliers ───

async def dso_components(dso: str) -> list[dict[str, Any]]:
    return await _fetch_all(queries.DSO_BY_DSO, (dso,))


async def all_dso_tariffs() -> list[dict[str, Any]]:
    return await _fetch_all(queries.DSO_ALL)


async def get_supplier(supplier_id: int) -> dict[str, Any]:
    row = await _fetch_one(queries.SUPPLIER_BY_ID, (supplier_id,))
    if row is None:
        raise ValueError("supplier not found")
    return row


async def all_suppliers() -> list[dict[str, Any]]:
    return await _fetch_all(queries.SUPPLIER_ALL)


# ─── consumption (per-user) ───

async def upsert_consumption(user_id: int, rows: list[tuple[str, float]]) -> int:
    params = [(user_id, ts, kwh) for ts, kwh in rows]
    await _execute_many(queries.CONSUMPTION_UPSERT, params)
    return len(params)


async def consumption_range(user_id: int, start: str, end: str) -> list[dict[str, Any]]:
    return await _fetch_all(queries.CONSUMPTION_RANGE, (user_id, start, end))


async def consumption_all(user_id: int) -> list[dict[str, Any]]:
    return await _fetch_all(queries.CONSUMPTION_ALL, (user_id,))


async def consumption_count(user_id: int) -> int:
    return int(await _fetch_scalar(queries.CONSUMPTION_COUNT, (user_id,)) or 0)


# ─── forecasts ───

async def upsert_forecast(target_date: str, zone: str, direction: str,
                          confidence: float, basis: str | None) -> None:
    await _execute(queries.FORECAST_UPSERT, (target_date, zone, direction, confidence, basis))


async def upcoming_forecasts(zone: str, from_date: str, limit: int = 3) -> list[dict[str, Any]]:
    return await _fetch_all(queries.FORECAST_UPCOMING, (zone, from_date, limit))


# ─── source_cache ───

async def cache_put(key: str, payload: Any) -> None:
    await _execute(queries.CACHE_UPSERT, (key, json.dumps(payload)))


async def cache_get(key: str) -> dict[str, Any] | None:
    row = await _fetch_one(queries.CACHE_GET, (key,))
    if row is None:
        return None
    return {"payload": json.loads(row["payload"]), "fetched_at": row["fetched_at"]}


# ─── low-level helpers ───

async def _fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    conn = await _connect()
    try:
        cur = await conn.execute(sql, params)
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def _fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = await _connect()
    try:
        cur = await conn.execute(sql, params)
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await conn.close()


async def _fetch_scalar(sql: str, params: tuple = ()) -> Any:
    conn = await _connect()
    try:
        return await _scalar(conn, sql, params)
    finally:
        await conn.close()


async def _execute(sql: str, params: tuple = ()) -> None:
    conn = await _connect()
    try:
        await conn.execute(sql, params)
        await conn.commit()
    finally:
        await conn.close()


async def _execute_many(sql: str, params: list[tuple]) -> None:
    if not params:
        return
    conn = await _connect()
    try:
        await conn.executemany(sql, params)
        await conn.commit()
    finally:
        await conn.close()
