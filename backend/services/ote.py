"""OTE day-ahead spot client — thin transport + parse only.

Uses the spotovaelektrina.cz wrapper over OTE. Returns plain rows; persistence is db.py's job.
"""

from __future__ import annotations

import httpx

BASE_URL = "https://spotovaelektrina.cz/api/v1/price"
USER_AGENT = "Spotwise/0.1 (+https://spotwise.example)"
_TIMEOUT = httpx.Timeout(15.0)


async def fetch_day_ahead(date: str, zone: str = "CZ") -> list[tuple[str, str, float]]:
    """Fetch hourly/quarter-hourly day-ahead prices for ``date`` (YYYY-MM-DD).

    Returns [(ts_iso, zone, price_eur_mwh)]. Raises httpx.HTTPError on transport failure — the
    scheduler catches and logs; request paths never call this inline.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(f"{BASE_URL}/{date}")
        resp.raise_for_status()
        return _parse(resp.json(), date, zone)


def _parse(payload: dict, date: str, zone: str) -> list[tuple[str, str, float]]:
    """Normalize the wrapper's {hoursToday: [{hour, priceEUR}, ...]} shape."""
    rows: list[tuple[str, str, float]] = []
    for item in payload.get("hoursToday", []):
        hour = int(item["hour"])
        ts = f"{date}T{hour:02d}:00:00"
        rows.append((ts, zone, float(item["priceEUR"])))
    return rows
