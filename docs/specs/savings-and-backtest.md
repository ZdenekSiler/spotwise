# Spec: Personalized savings & backtested supplier ranking

Status: MVP. Owner module: `routers/savings_api.py` (+ `services/landed_cost.py`).

## Goal

Join the user's own 15-min consumption curve to a full historical spot series through **every
supplier's actual fee structure** → "you'd have paid X at Supplier A, Y at Supplier B",
ranked, plus a quantified negative-price ("free electricity") capture number.

## Computation

For each supplier over the backtest window (default: trailing 12 months of available spot):

```
cost = Σ_interval  consumption_kwh[i] * landed_czk_kwh(spot[i], fx[date(i)], dso, supplier)
     + monthly_fee * months_in_window
```

Reuses `landed_cost.compute_landed_cost` per interval (no duplicate arithmetic). Ranking is
ascending total cost. Savings vs the user's current supplier (if set) = current − best.

Negative-price capture: Σ over intervals where `spot < 0` of `abs(landed_czk_kwh) *
shiftable_kwh[i]`, where shiftable load is estimated from the consumption profile (initially a
simple flag/fraction; refined later). Report as "up to N Kč you could have captured".

## API

`GET /api/savings` (protected) →
`{ ranking: [{supplier, total_czk, vs_current_czk}], window, negative_capture_czk, sample }`.

## Dependencies / degradation

Needs uploaded consumption (else 400 "upload consumption first") and a spot history (else uses
what's cached, flags `partial_window`). Supplier numbers may be `sample`.

## Tests (`test_savings.py`)

Deterministic small fixture: known consumption + known spot + known suppliers → asserted
ranking and totals; negative-capture math; empty-consumption 400; per-user isolation.
