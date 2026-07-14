"""/api/savings — personalized savings + backtested supplier ranking. Protected."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

import models
from auth import current_user_id
from services import db, landed_cost

router = APIRouter(prefix="/api/savings", tags=["savings"])

DEFAULT_DSO = "CEZ"


@router.get("", response_model=models.SavingsOut)
async def get_savings(
    user_id: int = Depends(current_user_id),
    zone: str = Query("CZ"),
    dso: str = Query(DEFAULT_DSO),
):
    consumption = await db.consumption_all(user_id)
    if not consumption:
        raise HTTPException(status_code=400, detail="Nejprve nahrajte spotřebu")

    spot = await db.spot_all(zone)
    if not spot:
        raise HTTPException(status_code=409, detail="Chybí historická data cen")

    price_by_ts = {p["ts"]: p["price_eur_mwh"] for p in spot}
    fx_by_date, fx_fallback = await _fx_map(spot)
    dso_components = await db.dso_components(dso)
    suppliers = await db.all_suppliers()
    user = await db.get_user(user_id)

    cons = [(c["ts"], c["kwh"]) for c in consumption]
    matched = [ts for ts, _ in cons if ts in price_by_ts]
    partial = len(matched) < len(cons)
    months = max(len(set(ts[:7] for ts in matched)), 1)

    ranking = []
    current_total = None
    for s in suppliers:
        total = landed_cost.backtest_cost(
            cons, price_by_ts, fx_by_date, fx_fallback, dso_components, s, months
        )
        ranking.append((s, total))
        if user.get("current_supplier") == s["id"]:
            current_total = total

    ranking.sort(key=lambda r: r[1])
    ranked_out = [
        models.SupplierRankOut(
            supplier_id=s["id"], supplier=s["name"], total_czk=total,
            vs_current_czk=(round(current_total - total, 2) if current_total is not None else None),
            sample=bool(s["sample"]),
        )
        for s, total in ranking
    ]

    capture = landed_cost.negative_capture(cons, price_by_ts, fx_by_date, fx_fallback)
    return models.SavingsOut(
        window_months=months, partial_window=partial,
        ranking=ranked_out, negative_capture_czk=capture,
    )


async def _fx_map(spot: list[dict]) -> tuple[dict[str, float], float]:
    """Resolve an FX rate per distinct date in the spot series, with a latest-rate fallback."""
    fx_by_date: dict[str, float] = {}
    for day in sorted({p["ts"][:10] for p in spot}):
        row = await db.fx_on_or_before(day)
        if row:
            fx_by_date[day] = row["eur_czk"]
    fallback = next(iter(reversed(fx_by_date.values())), 25.0) if fx_by_date else 25.0
    return fx_by_date, fallback
