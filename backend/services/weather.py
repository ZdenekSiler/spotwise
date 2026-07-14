"""Open-Meteo weather client — thin transport + parse only. No API key needed.

Provides the solar-irradiance and wind-speed forecasts that feed the residual-load estimate.
"""

from __future__ import annotations

import httpx

BASE_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "Spotwise/0.1 (+https://spotwise.example)"
_TIMEOUT = httpx.Timeout(15.0)

# Rough centroid of the German bidding zone (dominant driver of CZ prices).
DE_LAT, DE_LON = 51.0, 10.0


async def fetch_forecast(lat: float = DE_LAT, lon: float = DE_LON,
                         days: int = 4) -> dict[str, list]:
    """Return hourly {time, shortwave_radiation, wind_speed_100m} for the horizon."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "shortwave_radiation,wind_speed_100m",
        "forecast_days": days,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("hourly", {})
