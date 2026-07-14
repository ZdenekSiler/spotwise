"""External source clients — transport + parse, HTTP mocked with respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from services import cnb, ote


@respx.mock
async def test_ote_fetch_day_ahead_parses_hours():
    from datetime import date, timedelta

    payload = {
        "hoursToday": [
            {"hour": 0, "priceEur": 100.0},
            {"hour": 1, "priceEur": 120.5},
        ],
        "hoursTomorrow": [
            {"hour": 0, "priceEur": 90.0},
        ],
    }
    respx.get(f"{ote.BASE_URL}/get-prices-json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    rows = await ote.fetch_day_ahead()
    assert rows[0] == (f"{today}T00:00:00", "CZ", 100.0)
    assert rows[1] == (f"{today}T01:00:00", "CZ", 120.5)
    assert rows[2] == (f"{tomorrow}T00:00:00", "CZ", 90.0)


@respx.mock
async def test_ote_skips_empty_tomorrow():
    payload = {"hoursToday": [{"hour": 0, "priceEur": 100.0}], "hoursTomorrow": []}
    respx.get(f"{ote.BASE_URL}/get-prices-json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    rows = await ote.fetch_day_ahead()
    assert len(rows) == 1


@respx.mock
async def test_ote_raises_on_http_error():
    respx.get(f"{ote.BASE_URL}/get-prices-json").mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPError):
        await ote.fetch_day_ahead()


@respx.mock
async def test_cnb_parses_eur_row():
    feed = (
        "14 Jul 2025 #135\n"
        "Country|Currency|Amount|Code|Rate\n"
        "EMU|euro|1|EUR|25.340\n"
        "USA|dollar|1|USD|23.100\n"
    )
    respx.get(cnb.BASE_URL).mock(return_value=httpx.Response(200, text=feed))
    assert await cnb.fetch_eur_czk() == 25.34


@respx.mock
async def test_cnb_raises_when_eur_missing():
    respx.get(cnb.BASE_URL).mock(return_value=httpx.Response(200, text="no eur here"))
    with pytest.raises(ValueError):
        await cnb.fetch_eur_czk()
