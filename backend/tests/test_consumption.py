"""Consumption CSV upload + read, tolerant parsing, isolation."""

from __future__ import annotations

from routers import consumption_api


def test_parse_csv_handles_semicolon_and_comma_decimal():
    raw = b"cas;spotreba\n01.01.2025 00:00;1,5\n01.01.2025 00:15;2,0\n"
    rows = consumption_api._parse_csv(raw)
    assert rows == [("2025-01-01T00:00:00", 1.5), ("2025-01-01T00:15:00", 2.0)]


def test_parse_csv_handles_iso_and_comma_delimiter():
    raw = b"ts,kwh\n2025-01-01T00:00:00,1.5\n2025-01-01T00:15:00,2.0\n"
    rows = consumption_api._parse_csv(raw)
    assert rows == [("2025-01-01T00:00:00", 1.5), ("2025-01-01T00:15:00", 2.0)]


def test_parse_csv_skips_header_and_malformed_lines():
    raw = b"timestamp,value\nnot-a-date,x\n2025-01-01T00:00:00,3.0\n"
    rows = consumption_api._parse_csv(raw)
    assert rows == [("2025-01-01T00:00:00", 3.0)]


async def test_upload_and_read_roundtrip(auth_client):
    csv = b"ts,kwh\n2025-01-01T00:00:00,1.5\n2025-01-01T00:15:00,2.0\n"
    up = await auth_client.post(
        "/api/consumption", files={"file": ("meter.csv", csv, "text/csv")}
    )
    assert up.status_code == 200
    assert up.json()["rows_imported"] == 2

    series = await auth_client.get("/api/consumption")
    assert series.status_code == 200
    assert len(series.json()) == 2


async def test_upload_empty_csv_is_unprocessable(auth_client):
    resp = await auth_client.post(
        "/api/consumption", files={"file": ("m.csv", b"header,only\n", "text/csv")}
    )
    assert resp.status_code == 422
