"""/api/consumption — smart-meter CSV upload + read. Protected, per-user isolated."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

import models
from auth import current_user_id
from services import db

router = APIRouter(prefix="/api/consumption", tags=["consumption"])

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB upload cap (untrusted input)


@router.post("", response_model=models.ConsumptionUploadOut)
async def upload(file: UploadFile, user_id: int = Depends(current_user_id)):
    raw = await file.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Soubor je příliš velký")
    rows = _parse_csv(raw)
    if not rows:
        raise HTTPException(status_code=422, detail="Nepodařilo se načíst žádná data")
    imported = await db.upsert_consumption(user_id, rows)
    total = await db.consumption_count(user_id)
    return models.ConsumptionUploadOut(rows_imported=imported, total_rows=total)


@router.get("", response_model=list[models.ConsumptionPointOut])
async def series(
    user_id: int = Depends(current_user_id),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    if from_ and to:
        rows = await db.consumption_range(user_id, from_, to)
    else:
        rows = await db.consumption_all(user_id)
    return [models.ConsumptionPointOut(ts=r["ts"], kwh=r["kwh"]) for r in rows]


# ─── CSV parsing (tolerant of distributor export variants) ───

_TS_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
               "%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S")


def _parse_csv(raw: bytes) -> list[tuple[str, float]]:
    text = raw.decode("utf-8-sig", errors="replace")
    delimiter = ";" if text.count(";") > text.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    out: list[tuple[str, float]] = []
    for row in reader:
        if len(row) < 2:
            continue
        ts = _parse_ts(row[0].strip())
        kwh = _parse_float(row[1].strip())
        if ts is None or kwh is None:
            continue  # header or malformed line
        out.append((ts, kwh))
    return out


def _parse_ts(value: str) -> str | None:
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None


def _parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None
