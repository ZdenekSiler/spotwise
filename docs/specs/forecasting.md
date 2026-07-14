# Spec: Directional forecast (day+2 / day+3)

Status: MVP (differentiated). Owner modules: `services/forecast.py`, `services/entsoe.py`,
`services/weather.py`, `routers/forecast_api.py`.

## Goal

OTE only tells you tomorrow. Czech prices track **German residual load** (interconnected grid;
DE solar/wind dominates Central-European price swings). Combining ENTSO-E DE/AT
generation-by-fuel + load with Open-Meteo weather yields a **directional** signal for
day+2/day+3 — "next Tuesday looks oversupplied, worth deferring the EV charge" — that no single
source gives.

## Method (`compute_direction`, pure)

```
residual_load = forecast_load − forecast_wind − forecast_solar     (from ENTSO-E + weather)
```

Map residual load (normalized against the recent distribution) to a direction:
`cheap` / `neutral` / `expensive`, plus a `confidence` from input freshness/agreement. This is
intentionally **directional, not a price** — honest about the horizon's uncertainty. Store in
`forecasts(target_date, zone, direction, confidence, basis)`.

## API

`GET /api/forecast?zone=CZ` (public) → next 3 days of `{target_date, direction, confidence,
basis}`. Day+1 uses the published day-ahead (if available) rather than the model.

## Degradation

If `ENTSOE_API_TOKEN` is absent or ENTSO-E/Open-Meteo fail: return day-ahead-only with
`direction: "unknown"` for day+2/+3 and `degraded: true`. Never 500 on missing token.

## Scheduling

`services/scheduler.py` refreshes ENTSO-E + weather caches on the forecast horizon and
recomputes `forecasts`. Cache-then-serve: the router reads `forecasts`/caches, never calls
external APIs inline.

## Tests (`test_forecast.py`)

`compute_direction` on synthetic residual-load fixtures (oversupply→cheap, tight→expensive);
degradation path with no token (respx returns error → `degraded: true`, no exception).
