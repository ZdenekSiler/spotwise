"""HTTP surface: health, prices, tariffs, forecast (public) + savings (protected)."""

from __future__ import annotations

from services import db


async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_tariffs_returns_sample_suppliers(client):
    resp = await client.get("/api/tariffs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["suppliers"]) >= 1
    assert body["suppliers"][0]["sample"] is True


async def test_prices_returns_landed_tiles_sorted(client):
    await db.upsert_spot_prices([
        ("2025-06-01T00:00:00", "CZ", 100.0),
        ("2025-06-01T01:00:00", "CZ", 200.0),
    ])
    await db.upsert_fx("2025-06-01", 25.0)

    resp = await client.get("/api/prices", params={"date": "2025-06-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["fx_stale"] is False
    assert len(body["series"]) == 2
    tiles = body["tiles"]
    assert tiles == sorted(tiles, key=lambda t: t["avg_landed_czk_kwh"])


async def test_prices_flags_stale_fx_when_missing(client):
    await db.upsert_spot_prices([("2025-06-02T00:00:00", "CZ", 100.0)])
    resp = await client.get("/api/prices", params={"date": "2025-06-02"})
    assert resp.json()["fx_stale"] is True


async def test_forecast_is_degraded_without_token(client):
    resp = await client.get("/api/forecast")
    assert resp.status_code == 200
    assert resp.json()["degraded"] is True


async def test_savings_requires_consumption(auth_client):
    resp = await auth_client.get("/api/savings")
    assert resp.status_code == 400


async def test_savings_ranks_suppliers(auth_client):
    # Seed a small spot history + FX, then upload matching consumption.
    await db.upsert_spot_prices([
        ("2025-03-01T00:00:00", "CZ", 100.0),
        ("2025-03-01T01:00:00", "CZ", 150.0),
    ])
    await db.upsert_fx("2025-03-01", 25.0)
    csv = b"ts,kwh\n2025-03-01T00:00:00,2.0\n2025-03-01T01:00:00,2.0\n"
    await auth_client.post("/api/consumption", files={"file": ("m.csv", csv, "text/csv")})

    resp = await auth_client.get("/api/savings")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ranking"]) >= 1
    totals = [r["total_czk"] for r in body["ranking"]]
    assert totals == sorted(totals)  # ascending cost


async def test_set_current_supplier_updates_profile(auth_client):
    resp = await auth_client.put("/api/user/supplier", json={"supplier_id": 1})
    assert resp.status_code == 200
    assert resp.json()["current_supplier"] == 1
    # /auth/me reflects the change.
    me = await auth_client.get("/auth/me")
    assert me.json()["current_supplier"] == 1


async def test_set_current_supplier_unknown_returns_404(auth_client):
    resp = await auth_client.put("/api/user/supplier", json={"supplier_id": 99999})
    assert resp.status_code == 404


async def test_set_current_supplier_requires_auth(client):
    resp = await client.put("/api/user/supplier", json={"supplier_id": 1})
    assert resp.status_code == 401


async def test_savings_vs_current_populated_after_set(auth_client):
    await db.upsert_spot_prices([
        ("2025-03-01T00:00:00", "CZ", 100.0),
        ("2025-03-01T01:00:00", "CZ", 150.0),
    ])
    await db.upsert_fx("2025-03-01", 25.0)
    csv = b"ts,kwh\n2025-03-01T00:00:00,2.0\n2025-03-01T01:00:00,2.0\n"
    await auth_client.post("/api/consumption", files={"file": ("m.csv", csv, "text/csv")})
    await auth_client.put("/api/user/supplier", json={"supplier_id": 1})

    body = (await auth_client.get("/api/savings")).json()
    # The current supplier's own delta is 0; every row now carries a numeric delta.
    assert all(r["vs_current_czk"] is not None for r in body["ranking"])
    current = next(r for r in body["ranking"] if r["supplier_id"] == 1)
    assert current["vs_current_czk"] == 0.0
