"""ENTSO-E Transparency client — thin transport + parse only (no pandas).

Provides German/Austrian load forecast that drives Central-European price swings. Requires a
free token (email registration); callers degrade to day-ahead-only when it is absent.

We hit the Transparency REST API directly and parse the XML with the stdlib. This deliberately
avoids ``entsoe-py`` (which pulls in pandas + numpy — ~120 MB resident, heavy import) so the
service stays lean on a low-CPU host. See docs/data-sources.md.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx

import config

BASE_URL = "https://web-api.tp.entsoe.eu/api"
USER_AGENT = "Spotwise/0.1 (+https://spotwise.example)"
_TIMEOUT = httpx.Timeout(30.0)

# Bidding-zone EIC codes. DE_LU drives CZ prices; extend as needed.
_ZONE_EIC = {
    "DE_LU": "10Y1001A1001A82H",
    "CZ": "10YCZ-CEPS-----N",
    "AT": "10YAT-APG------L",
}


def is_available() -> bool:
    """True only if a token is configured. Callers degrade to day-ahead-only otherwise."""
    return config.entsoe_token() is not None


async def fetch_load_forecast(zone: str = "DE_LU", days: int = 4) -> list[float]:
    """Return day-ahead total-load-forecast values (MW) for the horizon.

    Raises RuntimeError if no token is configured, or httpx.HTTPError on transport failure — the
    caller catches and degrades. Never called inline in a request path.
    """
    token = config.entsoe_token()
    if token is None:
        raise RuntimeError("ENTSO-E token not configured")

    domain = _ZONE_EIC.get(zone, zone)
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)
    params = {
        "securityToken": token,
        "documentType": "A65",   # System total load
        "processType": "A01",    # Day-ahead
        "outBiddingZone_Domain": domain,
        "periodStart": start.strftime("%Y%m%d%H%M"),
        "periodEnd": end.strftime("%Y%m%d%H%M"),
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return _parse_quantities(resp.text)


def _parse_quantities(xml_text: str) -> list[float]:
    """Extract ordered ``<quantity>`` values from the Points of every TimeSeries/Period.

    Namespace-agnostic: ENTSO-E stamps a versioned namespace on every tag, so we match by the
    local tag name rather than binding to a specific schema version.
    """
    root = ET.fromstring(xml_text)
    quantities: list[float] = []
    for elem in root.iter():
        if _local(elem.tag) == "quantity" and elem.text:
            quantities.append(float(elem.text))
    return quantities


def _local(tag: str) -> str:
    """Strip the ``{namespace}`` prefix ElementTree prepends to every tag."""
    return tag.rsplit("}", 1)[-1]
