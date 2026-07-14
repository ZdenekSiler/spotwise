"""Forecast fusion — pure computation, no DB, no HTTP.

Maps a residual-load estimate (load − wind − solar) into a directional price signal for
day+2/day+3. Intentionally directional, not a price: honest about the horizon's uncertainty.

See docs/specs/forecasting.md.
"""

from __future__ import annotations

from dataclasses import dataclass

CHEAP = "cheap"
NEUTRAL = "neutral"
EXPENSIVE = "expensive"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Direction:
    direction: str
    confidence: float
    basis: str


def residual_load(load_mw: float, wind_mw: float, solar_mw: float) -> float:
    """Demand not covered by renewables. Higher → tighter market → dearer prices."""
    return load_mw - wind_mw - solar_mw


def compute_direction(
    residual: float,
    recent_mean: float,
    recent_std: float,
    freshness: float = 1.0,
) -> Direction:
    """Classify residual load vs the recent distribution into cheap/neutral/expensive.

    ``freshness`` in [0, 1] scales confidence (stale/partial inputs → lower confidence).
    A residual well below the recent mean means oversupply → cheap; well above → expensive.
    """
    if recent_std <= 0:
        z = 0.0
    else:
        z = (residual - recent_mean) / recent_std

    if z <= -0.5:
        direction = CHEAP
    elif z >= 0.5:
        direction = EXPENSIVE
    else:
        direction = NEUTRAL

    confidence = round(max(0.0, min(1.0, min(abs(z), 2.0) / 2.0)) * freshness, 3)
    basis = f"residual_load z={z:+.2f}"
    return Direction(direction=direction, confidence=confidence, basis=basis)


def degraded_direction(reason: str = "no ENTSO-E token") -> Direction:
    """Fallback when ENTSO-E/weather are unavailable — never raise."""
    return Direction(direction=UNKNOWN, confidence=0.0, basis=f"degraded: {reason}")
