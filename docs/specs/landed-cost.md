# Spec: Landed cost & day-ahead prices

Status: foundation (MVP). Owner module: `services/landed_cost.py`, `routers/prices_api.py`.

## Goal

Turn the raw OTE day-ahead spot price into the number that actually matters: **Kč/kWh landing
in the user's account**, per supplier, and expose the spot series + fused tiles.

## Inputs

- `spot_prices(ts, zone, price_eur_mwh)` — OTE day-ahead (15-min), zone `CZ`.
- `fx_rates(date, eur_czk)` — ČNB daily.
- `dso_tariffs(dso, component, czk_per_kwh, czk_per_month)` — regulated distribution.
- `suppliers(id, name, markup_czk_mwh, monthly_fee_czk, product)` — dynamic-tariff price list.

## Computation (`compute_landed_cost`)

For a given interval and supplier/DSO:

```
spot_czk_kwh   = price_eur_mwh * eur_czk(date) / 1000
supplier_czk   = markup_czk_mwh / 1000
distribution   = Σ dso component czk_per_kwh
fixed_daily    = (monthly_fee_czk + Σ dso czk_per_month) / days_in_month / 24  (per hour, informational)
landed_czk_kwh = spot_czk_kwh + supplier_czk + distribution   (+ VAT if configured)
```

Pure function: takes the four values, returns a `LandedCost` model. No DB, no FX lookup
inside — the router resolves the FX rate for the matching date and passes it in.

## API

`GET /api/prices?zone=CZ&date=YYYY-MM-DD&supplier=<id>` →
`{ series: [{ts, price_eur_mwh, landed_czk_kwh}], tiles: [{supplier, avg_landed, min, max}] }`.
Defaults to today/tomorrow if published. Public.

## Edge cases

- FX missing for a date → use most recent prior rate; flag `fx_stale: true`.
- Sample tariffs/suppliers → propagate `sample: true` into the response.
- Negative spot → landed cost can go negative; do not clamp (that's the "free electricity" signal).

## Tests (`test_landed_cost.py`)

EUR→CZK→kWh arithmetic; component summation; negative-spot passthrough; stale-FX fallback.
100% coverage (pure util).
