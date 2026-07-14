# Data sources

Every external source Spotwise consumes, how it is accessed, its cadence, and the rules for
scraping the ones without an API. See also [`../DESIGN.md`](../DESIGN.md) §2.

## Clients (thin wrappers, `backend/services/`)

| Source | Module | Auth | Cadence pulled | Cache |
| --- | --- | --- | --- | --- |
| OTE day-ahead + intraday | `ote.py` | none | ~13:00 daily (next day) via scheduler | `spot_prices` |
| ENTSO-E Transparency | `entsoe.py` | `ENTSOE_API_TOKEN` (free, email) | with forecast horizon | `entsoe_cache` |
| Open-Meteo | `weather.py` | none | with forecast horizon | `weather_cache` |
| ČNB EUR/CZK | `cnb.py` | none | daily | `fx_rates` |

**Client convention:** clients only do transport + parse into plain dicts/values; they never
persist, fuse, or raise `HTTPException`. Persistence is `db.py`'s job; fusion is
`landed_cost.py` / `forecast.py`. All clients use one shared `httpx.AsyncClient` with a
timeout and a descriptive `User-Agent`. **Cache-then-serve:** routers read from SQLite; the
scheduler refreshes the cache. A missing token/network failure must degrade gracefully, not
500 (forecast falls back to day-ahead-only).

**No heavy client libraries.** `entsoe.py` hits the ENTSO-E Transparency REST API directly with
`httpx` and parses the XML with the stdlib (`xml.etree`) — we deliberately do **not** use
`entsoe-py`, because it pulls in pandas + numpy (~120 MB resident, heavy cold import) for what is
a thin transport+parse job. Spotwise targets a low-CPU host (Hetzner CX-class shared vCPU), so a
new source client must stay dependency-light: reach for the stdlib parser before adding a library.

## EUR → CZK correctness

OTE settles in **EUR/MWh**. Landed cost must convert with the ČNB rate **for the matching
day**, then divide by 1000 for kWh, then add DSO tariff components (Kč/kWh + monthly fee
amortized) and the supplier markup. Never mix a EUR spot value with a Kč tariff without the
FX step. This invariant is unit-tested in `test_landed_cost.py`.

## Scraped sources (ERÚ tariffs, supplier ceníky)

These have no API. For the MVP they ship as **seed JSON marked `"sample": true`**
(`backend/seed/{dso_tariffs.json,suppliers.json}`), loaded by `init_db()` into the
`dso_tariffs` / `suppliers` tables only when empty. Live scraping is a follow-up; when built
it must:

- Respect `robots.txt` and a conservative rate limit (≥1 request / few seconds per host).
- Send a descriptive `User-Agent` identifying Spotwise + contact.
- Cache aggressively (these update annually / irregularly — do not poll frequently).
- Store the source URL + fetch date alongside each record for auditability.
- Never present scraped/sample numbers as authoritative without the `sample`/`as_of` flag
  surfaced to the user.
