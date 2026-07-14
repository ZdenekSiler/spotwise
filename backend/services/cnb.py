"""ČNB EUR/CZK daily rate client — thin transport + parse only.

The ČNB publishes a semicolon-delimited text feed. We extract the EUR row.
"""

from __future__ import annotations

import httpx

BASE_URL = "https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/daily.txt"
USER_AGENT = "Spotwise/0.1 (+https://spotwise.example)"
_TIMEOUT = httpx.Timeout(15.0)


async def fetch_eur_czk() -> float:
    """Return today's EUR→CZK rate. Raises on transport/parse failure."""
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(BASE_URL)
        resp.raise_for_status()
        return _parse_eur(resp.text)


def _parse_eur(text: str) -> float:
    """Feed rows look like ``EMU|euro|1|EUR|25.340``; amount / rate = CZK per 1 EUR."""
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) == 5 and parts[3] == "EUR":
            amount = float(parts[2])
            rate = float(parts[4].replace(",", "."))
            return round(rate / amount, 4)
    raise ValueError("EUR rate not found in ČNB feed")
