"""Data layer: schema, seed, upserts, FX fallback, per-user isolation."""

from __future__ import annotations

import pytest

from services import db


async def test_init_db_loads_sample_seed():
    await db.init_db()
    suppliers = await db.all_suppliers()
    tariffs = await db.all_dso_tariffs()
    assert len(suppliers) >= 1
    assert all(s["sample"] == 1 for s in suppliers)
    assert any(t["dso"] == "CEZ" for t in tariffs)


async def test_spot_upsert_and_range_is_ordered():
    await db.init_db()
    await db.upsert_spot_prices([
        ("2025-01-01T01:00:00", "CZ", 120.0),
        ("2025-01-01T00:00:00", "CZ", 100.0),
    ])
    rows = await db.spot_range("CZ", "2025-01-01T00:00:00", "2025-01-01T23:59:59")
    assert [r["ts"] for r in rows] == ["2025-01-01T00:00:00", "2025-01-01T01:00:00"]


async def test_fx_on_or_before_falls_back_to_prior_date():
    await db.init_db()
    await db.upsert_fx("2025-01-01", 25.0)
    row = await db.fx_on_or_before("2025-01-05")
    assert row["eur_czk"] == 25.0


async def test_create_user_rejects_duplicate_email():
    await db.init_db()
    await db.create_user("a@b.cz", "hash")
    with pytest.raises(ValueError):
        await db.create_user("a@b.cz", "hash2")


async def test_consumption_is_isolated_per_user():
    await db.init_db()
    u1 = await db.create_user("u1@b.cz", "h")
    u2 = await db.create_user("u2@b.cz", "h")
    await db.upsert_consumption(u1, [("2025-01-01T00:00:00", 1.0)])
    await db.upsert_consumption(u2, [("2025-01-01T00:00:00", 9.0)])
    assert await db.consumption_count(u1) == 1
    rows = await db.consumption_all(u1)
    assert rows[0]["kwh"] == 1.0  # cannot see u2's row


async def test_upsert_consumption_is_idempotent():
    await db.init_db()
    uid = await db.create_user("x@b.cz", "h")
    await db.upsert_consumption(uid, [("2025-01-01T00:00:00", 1.0)])
    await db.upsert_consumption(uid, [("2025-01-01T00:00:00", 2.0)])
    assert await db.consumption_count(uid) == 1
    assert (await db.consumption_all(uid))[0]["kwh"] == 2.0
