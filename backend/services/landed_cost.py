"""Landed-cost fusion — pure computation, no DB, no HTTP.

Turns a EUR/MWh spot price into the Kč/kWh landing in the user's account by adding the ČNB FX
conversion, the DSO distribution components, and the supplier markup. This is the correctness
core; it is unit-tested to 100%.

See docs/specs/landed-cost.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LandedCost:
    spot_czk_kwh: float
    supplier_czk_kwh: float
    distribution_czk_kwh: float
    landed_czk_kwh: float
    fixed_czk_per_month: float


def spot_to_czk_kwh(price_eur_mwh: float, eur_czk: float) -> float:
    """EUR/MWh → Kč/kWh. Never mix EUR and Kč without this step."""
    return price_eur_mwh * eur_czk / 1000.0


def compute_landed_cost(
    price_eur_mwh: float,
    eur_czk: float,
    dso_components: list[dict],
    supplier: dict,
    vat_rate: float = 0.0,
) -> LandedCost:
    """Fuse one interval's spot price with FX, distribution tariff, and supplier markup.

    ``dso_components`` is a list of {czk_per_kwh, czk_per_month}. ``supplier`` has
    ``markup_czk_mwh`` and ``monthly_fee_czk``. VAT is applied to the variable Kč/kWh if given.
    Negative spot is passed through (do not clamp — it is the "free electricity" signal).
    """
    spot = spot_to_czk_kwh(price_eur_mwh, eur_czk)
    supplier_var = supplier.get("markup_czk_mwh", 0.0) / 1000.0
    distribution = sum(c.get("czk_per_kwh", 0.0) for c in dso_components)
    fixed_month = supplier.get("monthly_fee_czk", 0.0) + sum(
        c.get("czk_per_month", 0.0) for c in dso_components
    )

    variable = spot + supplier_var + distribution
    if vat_rate:
        variable *= 1.0 + vat_rate

    return LandedCost(
        spot_czk_kwh=round(spot, 4),
        supplier_czk_kwh=round(supplier_var, 4),
        distribution_czk_kwh=round(distribution, 4),
        landed_czk_kwh=round(variable, 4),
        fixed_czk_per_month=round(fixed_month, 2),
    )


def backtest_cost(
    consumption: list[tuple[str, float]],
    price_by_ts: dict[str, float],
    fx_by_date: dict[str, float],
    fx_fallback: float,
    dso_components: list[dict],
    supplier: dict,
    months: float,
) -> float:
    """Total Kč a user would have paid at ``supplier`` over their consumption curve.

    ``consumption`` is [(ts, kwh)]; ``price_by_ts`` maps ts→EUR/MWh; ``fx_by_date`` maps the
    date part of a ts→EUR/CZK (``fx_fallback`` used when a date is missing). Adds the fixed
    monthly fee × ``months``. Reuses compute_landed_cost so the arithmetic lives in one place.
    """
    total = 0.0
    fixed_month = supplier.get("monthly_fee_czk", 0.0) + sum(
        c.get("czk_per_month", 0.0) for c in dso_components
    )
    for ts, kwh in consumption:
        price = price_by_ts.get(ts)
        if price is None:
            continue
        eur_czk = fx_by_date.get(ts[:10], fx_fallback)
        lc = compute_landed_cost(price, eur_czk, dso_components, supplier)
        total += lc.landed_czk_kwh * kwh
    return round(total + fixed_month * months, 2)


def negative_capture(
    consumption: list[tuple[str, float]],
    price_by_ts: dict[str, float],
    fx_by_date: dict[str, float],
    fx_fallback: float,
    shiftable_fraction: float = 0.3,
) -> float:
    """Kč a user could have captured during negative-price intervals.

    Sums |spot Kč/kWh| × shiftable kWh over intervals where the spot price is negative.
    """
    captured = 0.0
    for ts, kwh in consumption:
        price = price_by_ts.get(ts)
        if price is None or price >= 0:
            continue
        eur_czk = fx_by_date.get(ts[:10], fx_fallback)
        spot = spot_to_czk_kwh(price, eur_czk)
        captured += abs(spot) * kwh * shiftable_fraction
    return round(captured, 2)
