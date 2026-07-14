---
name: simplify
description: Review recently changed code for quality, reuse, and efficiency. Find and fix over-engineering, duplication, and unnecessary complexity. Run this after /implement.
---

# /simplify

Post-implementation quality pass on the current diff. Quality only — this does not hunt for
bugs (use `/security-review` and tests for that).

## Look for

- **Duplication** — especially landed-cost / FX arithmetic reimplemented instead of calling
  `services/landed_cost.compute_landed_cost`.
- **Single-use abstractions** — a helper/class used once; inline it.
- **Fat clients** — a source client doing persistence or fusion; move it to `db.py` /
  `landed_cost.py` / `forecast.py`.
- **Inline SQL** — any SQL outside `queries.py`; hoist it to a named constant.
- **`fastapi` leaking into `db.py`** — revert; raise `ValueError` and translate in the router.
- **Inline external calls in request paths** — should be cache-then-serve via the scheduler.
- Dead code, commented-out code, unused imports, needless async/await.

## Do

Apply the fixes directly, keep the diff minimal, and re-run `make test` to confirm green.
