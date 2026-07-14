"""Forecast direction fusion + degradation path."""

from __future__ import annotations

from services import forecast


def test_residual_load_subtracts_renewables():
    assert forecast.residual_load(50000, 12000, 8000) == 30000


def test_compute_direction_oversupply_is_cheap():
    d = forecast.compute_direction(residual=30000, recent_mean=40000, recent_std=5000)
    assert d.direction == forecast.CHEAP
    assert 0 < d.confidence <= 1


def test_compute_direction_tight_market_is_expensive():
    d = forecast.compute_direction(residual=50000, recent_mean=40000, recent_std=5000)
    assert d.direction == forecast.EXPENSIVE


def test_compute_direction_near_mean_is_neutral():
    d = forecast.compute_direction(residual=41000, recent_mean=40000, recent_std=5000)
    assert d.direction == forecast.NEUTRAL


def test_compute_direction_zero_std_is_neutral():
    d = forecast.compute_direction(residual=40000, recent_mean=40000, recent_std=0)
    assert d.direction == forecast.NEUTRAL
    assert d.confidence == 0.0


def test_freshness_scales_confidence_down():
    fresh = forecast.compute_direction(30000, 40000, 5000, freshness=1.0)
    stale = forecast.compute_direction(30000, 40000, 5000, freshness=0.5)
    assert stale.confidence < fresh.confidence


def test_degraded_direction_is_unknown_and_never_raises():
    d = forecast.degraded_direction("no token")
    assert d.direction == forecast.UNKNOWN
    assert d.confidence == 0.0
