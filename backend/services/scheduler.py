"""APScheduler jobs — the only place external sources are pulled.

Cache-then-serve: these jobs refresh SQLite; request paths read the cache. Every job catches
its own errors and logs — a source outage must never crash the app.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services import cnb, db, ote

log = logging.getLogger("spotwise.scheduler")
_scheduler: AsyncIOScheduler | None = None


def start() -> AsyncIOScheduler:
    """Wire and start the background jobs. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = AsyncIOScheduler(timezone="Europe/Prague")
    # OTE publishes next-day prices ~13:00; pull a bit after.
    sched.add_job(refresh_spot_prices, "cron", hour=13, minute=30, id="ote")
    sched.add_job(refresh_fx, "cron", hour=15, minute=0, id="cnb")
    sched.start()
    _scheduler = sched
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


# ─── Jobs ───

async def refresh_spot_prices() -> None:
    """Fetch today's + tomorrow's day-ahead prices into spot_prices."""
    for day in (date.today(), date.today() + timedelta(days=1)):
        try:
            rows = await ote.fetch_day_ahead(day.isoformat())
            await db.upsert_spot_prices(rows)
            log.info("OTE: stored %d prices for %s", len(rows), day)
        except Exception as exc:  # noqa: BLE001 — jobs must not crash the app
            log.warning("OTE refresh failed for %s: %s", day, exc)


async def refresh_fx() -> None:
    """Fetch today's ČNB EUR/CZK into fx_rates."""
    try:
        rate = await cnb.fetch_eur_czk()
        await db.upsert_fx(date.today().isoformat(), rate)
        log.info("ČNB: EUR/CZK = %.4f", rate)
    except Exception as exc:  # noqa: BLE001
        log.warning("ČNB refresh failed: %s", exc)
