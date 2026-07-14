"""Pydantic domain models. *In for request bodies, *Out for responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ─── prices ───

class PricePointOut(_Base):
    ts: str
    price_eur_mwh: float
    landed_czk_kwh: float | None = None


class SupplierTileOut(_Base):
    supplier_id: int
    supplier: str
    avg_landed_czk_kwh: float
    min_landed_czk_kwh: float
    max_landed_czk_kwh: float
    sample: bool = False


class PricesOut(_Base):
    zone: str
    date: str
    fx_stale: bool = False
    series: list[PricePointOut]
    tiles: list[SupplierTileOut]


# ─── tariffs ───

class SupplierOut(_Base):
    id: int
    name: str
    product: str | None = None
    markup_czk_mwh: float
    monthly_fee_czk: float
    sample: bool = False


class TariffsOut(_Base):
    dso_tariffs: list[dict]
    suppliers: list[SupplierOut]


# ─── consumption ───

class ConsumptionPointOut(_Base):
    ts: str
    kwh: float


class ConsumptionUploadOut(_Base):
    rows_imported: int
    total_rows: int


# ─── savings ───

class SupplierRankOut(_Base):
    supplier_id: int
    supplier: str
    total_czk: float
    vs_current_czk: float | None = None
    sample: bool = False


class SavingsOut(_Base):
    window_months: float
    partial_window: bool
    ranking: list[SupplierRankOut]
    negative_capture_czk: float


# ─── user ───

class CurrentSupplierIn(_Base):
    supplier_id: int


class UserProfileOut(_Base):
    id: int
    email: str
    current_supplier: int | None = None


# ─── forecast ───

class ForecastDayOut(_Base):
    target_date: str
    direction: str
    confidence: float
    basis: str | None = None


class ForecastOut(_Base):
    zone: str
    degraded: bool
    days: list[ForecastDayOut]
