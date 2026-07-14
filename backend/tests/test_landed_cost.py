"""Landed-cost fusion — the correctness core (100% coverage target)."""

from __future__ import annotations

from services import landed_cost


def test_spot_to_czk_kwh_converts_eur_mwh_to_czk_kwh():
    # 100 EUR/MWh at 25 CZK/EUR = 2500 CZK/MWh = 2.5 CZK/kWh
    assert landed_cost.spot_to_czk_kwh(100.0, 25.0) == 2.5


def test_compute_landed_cost_sums_all_components():
    dso = [{"czk_per_kwh": 1.85, "czk_per_month": 0},
           {"czk_per_kwh": 0.60, "czk_per_month": 250}]
    supplier = {"markup_czk_mwh": 200, "monthly_fee_czk": 89}
    lc = landed_cost.compute_landed_cost(100.0, 25.0, dso, supplier)

    assert lc.spot_czk_kwh == 2.5
    assert lc.supplier_czk_kwh == 0.2          # 200 / 1000
    assert lc.distribution_czk_kwh == 2.45     # 1.85 + 0.60
    assert lc.landed_czk_kwh == 5.15           # 2.5 + 0.2 + 2.45
    assert lc.fixed_czk_per_month == 339.0     # 89 + 250


def test_compute_landed_cost_applies_vat_to_variable():
    lc = landed_cost.compute_landed_cost(
        100.0, 25.0, [{"czk_per_kwh": 0}], {"markup_czk_mwh": 0}, vat_rate=0.21
    )
    assert lc.landed_czk_kwh == round(2.5 * 1.21, 4)


def test_compute_landed_cost_passes_through_negative_spot():
    lc = landed_cost.compute_landed_cost(
        -50.0, 25.0, [{"czk_per_kwh": 0.5}], {"markup_czk_mwh": 100}
    )
    # spot -1.25 + supplier 0.1 + dist 0.5 = -0.65 (not clamped)
    assert lc.landed_czk_kwh == -0.65


def test_backtest_cost_uses_matching_fx_and_adds_fixed_fee():
    cons = [("2025-01-01T00:00:00", 2.0), ("2025-01-01T01:00:00", 1.0)]
    prices = {"2025-01-01T00:00:00": 100.0, "2025-01-01T01:00:00": 200.0}
    fx = {"2025-01-01": 25.0}
    dso = [{"czk_per_kwh": 1.0, "czk_per_month": 100}]
    supplier = {"markup_czk_mwh": 0, "monthly_fee_czk": 50}

    # interval 0: (2.5 + 1.0) * 2 = 7.0 ; interval 1: (5.0 + 1.0) * 1 = 6.0 ; fixed 150 * 1
    total = landed_cost.backtest_cost(cons, prices, fx, 25.0, dso, supplier, months=1)
    assert total == 163.0


def test_backtest_cost_skips_intervals_without_price():
    cons = [("2025-01-01T00:00:00", 5.0)]
    total = landed_cost.backtest_cost(cons, {}, {}, 25.0, [], {"monthly_fee_czk": 0}, months=1)
    assert total == 0.0


def test_negative_capture_only_counts_negative_intervals():
    cons = [("2025-01-01T00:00:00", 4.0), ("2025-01-01T01:00:00", 4.0)]
    prices = {"2025-01-01T00:00:00": -40.0, "2025-01-01T01:00:00": 40.0}
    fx = {"2025-01-01": 25.0}
    # negative interval: |(-40*25/1000)| = 1.0 CZK/kWh * 4 kWh * 0.3 = 1.2
    captured = landed_cost.negative_capture(cons, prices, fx, 25.0, shiftable_fraction=0.3)
    assert captured == 1.2
