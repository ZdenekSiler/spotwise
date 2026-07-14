"""/api/forecast — day+2/+3 directional forecast. Public, cache-then-serve, degrades."""

from __future__ import annotations

from datetime import date as date_cls

from fastapi import APIRouter, Query

import models
from services import db, entsoe

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("", response_model=models.ForecastOut)
async def get_forecast(zone: str = Query("CZ")):
    today = date_cls.today().isoformat()
    rows = await db.upcoming_forecasts(zone, today, limit=3)
    days = [
        models.ForecastDayOut(
            target_date=r["target_date"], direction=r["direction"],
            confidence=r["confidence"], basis=r["basis"],
        )
        for r in rows
    ]
    # Without a token (or without a computed horizon) we serve day-ahead only.
    degraded = not entsoe.is_available() or not days
    return models.ForecastOut(zone=zone, degraded=degraded, days=days)
