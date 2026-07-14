"""/api/tariffs — regulated DSO tariffs + supplier price lists. Public."""

from __future__ import annotations

from fastapi import APIRouter

import models
from services import db

router = APIRouter(prefix="/api/tariffs", tags=["tariffs"])


@router.get("", response_model=models.TariffsOut)
async def get_tariffs():
    dso = await db.all_dso_tariffs()
    suppliers = await db.all_suppliers()
    return models.TariffsOut(
        dso_tariffs=dso,
        suppliers=[
            models.SupplierOut(
                id=s["id"], name=s["name"], product=s["product"],
                markup_czk_mwh=s["markup_czk_mwh"], monthly_fee_czk=s["monthly_fee_czk"],
                sample=bool(s["sample"]),
            )
            for s in suppliers
        ],
    )
