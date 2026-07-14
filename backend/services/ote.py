"""OTE day-ahead spot client — thin transport + parse only.

Uses the spotovaelektrina.cz wrapper over OTE. One call returns today's and (after ~13:00 CET)
tomorrow's hourly prices; we stamp each hour with the appropriate date. Persistence is db.py's job.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx

BASE_URL = "https://spotovaelektrina.cz/api/v1/price"
USER_AGENT = "Spotwise/0.1 (+https://spotwise.example)"
_TIMEOUT = httpx.Timeout(15.0)


async def fetch_day_ahead(zone: str = "CZ") -> list[tuple[str, str, float]]:
    """Fetch hourly day-ahead prices for today and tomorrow.

    Returns [(ts_iso, zone, price_eur_mwh)]. Raises httpx.HTTPError on transport failure — the
    scheduler catches and logs; request paths never call this inline.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(f"{BASE_URL}/get-prices-json")
        resp.raise_for_status()
        return _parse(resp.json(), zone)


def _parse(payload: dict, zone: str) -> list[tuple[str, str, float]]:
    """Normalize {hoursToday: [{hour, priceEur}, ...], hoursTomorrow: [...]}.

    hoursTomorrow is empty until OTE publishes next-day prices (~13:00 CET); we simply skip it.
    """
    today = date.today()
    rows: list[tuple[str, str, float]] = []
    for key, day in (("hoursToday", today), ("hoursTomorrow", today + timedelta(days=1))):
        for item in payload.get(key, []):
            hour = int(item["hour"])
            ts = f"{day.isoformat()}T{hour:02d}:00:00"
            rows.append((ts, zone, float(item["priceEur"])))
    return rows
