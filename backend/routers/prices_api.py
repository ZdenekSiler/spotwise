"""/api/prices — spot series + landed-cost tiles. Public, cache-then-serve."""

from __future__ import annotations

from datetime import date as date_cls

from fastapi import APIRouter, Query

import models
from services import db, landed_cost

router = APIRouter(prefix="/api/prices", tags=["prices"])

DEFAULT_DSO = "CEZ"


@router.get("", response_model=models.PricesOut)
async def get_prices(
    zone: str = Query("CZ"),
    date: str | None = Query(None, description="YYYY-MM-DD; defaults to today"),
    dso: str = Query(DEFAULT_DSO),
):
    day = date or date_cls.today().isoformat()
    start, end = f"{day}T00:00:00", f"{day}T23:59:59"

    spot = await db.spot_range(zone, start, end)
    fx_row = await db.fx_on_or_before(day)
    fx_stale = fx_row is None or fx_row["date"] != day
    eur_czk = fx_row["eur_czk"] if fx_row else 0.0

    dso_components = await db.dso_components(dso)
    suppliers = await db.all_suppliers()

    # Series is landed cost for the first (cheapest-markup) supplier, if any.
    ref_supplier = min(suppliers, key=lambda s: s["markup_czk_mwh"], default=None)
    series = [
        models.PricePointOut(
            ts=p["ts"],
            price_eur_mwh=p["price_eur_mwh"],
            landed_czk_kwh=(
                landed_cost.compute_landed_cost(
                    p["price_eur_mwh"], eur_czk, dso_components, ref_supplier
                ).landed_czk_kwh
                if ref_supplier and eur_czk
                else None
            ),
        )
        for p in spot
    ]

    tiles = _tiles(spot, eur_czk, dso_components, suppliers) if spot and eur_czk else []
    return models.PricesOut(
        zone=zone, date=day, fx_stale=fx_stale, series=series, tiles=tiles
    )


def _tiles(spot, eur_czk, dso_components, suppliers) -> list[models.SupplierTileOut]:
    tiles = []
    for s in suppliers:
        landed = [
            landed_cost.compute_landed_cost(
                p["price_eur_mwh"], eur_czk, dso_components, s
            ).landed_czk_kwh
            for p in spot
        ]
        tiles.append(
            models.SupplierTileOut(
                supplier_id=s["id"],
                supplier=s["name"],
                avg_landed_czk_kwh=round(sum(landed) / len(landed), 4),
                min_landed_czk_kwh=min(landed),
                max_landed_czk_kwh=max(landed),
                sample=bool(s["sample"]),
            )
        )
    return sorted(tiles, key=lambda t: t.avg_landed_czk_kwh)
