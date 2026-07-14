"""/api/user — authenticated user profile settings. Protected, per-user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import models
from auth import current_user_id
from services import db

router = APIRouter(prefix="/api/user", tags=["user"])


@router.put("/supplier", response_model=models.UserProfileOut)
async def set_supplier(
    body: models.CurrentSupplierIn,
    user_id: int = Depends(current_user_id),
):
    """Set the caller's current supplier — the baseline savings compares against."""
    try:
        await db.get_supplier(body.supplier_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Dodavatel nenalezen")
    await db.set_current_supplier(user_id, body.supplier_id)
    return await db.get_user(user_id)
