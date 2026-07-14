---
name: design
description: Design a feature or component before writing code. Launches parallel Explore agents to research the codebase, then produces a spec in docs/specs/<feature>.md. Use this before /implement for any non-trivial change.
context: fork
agent: Plan
argument-hint: <feature name or description>
---

# /design

Produce a written design spec for a feature **before** any code is written. Write only the
spec — no implementation.

## Steps

1. Restate the feature and its intent in one or two sentences.
2. Launch up to 3 **Explore** agents in parallel to research the relevant parts of the
   codebase: existing modules to reuse, the data sources involved (`docs/data-sources.md`),
   the router/service split (`.claude/rules/architecture.md`), and current schema
   (`services/queries.py`). Do not duplicate their work.
3. Read the critical files the agents surface.
4. Write `docs/specs/<feature>.md` following the shape of the existing specs
   (`docs/specs/landed-cost.md` is a good template): **Goal · Inputs · Computation/Method ·
   API · Degradation/edge cases · Tests**. Name concrete files to touch and functions to reuse
   (e.g. `landed_cost.compute_landed_cost`).
5. Respect the invariants in `.claude/rules/architecture.md` (thin clients, all SQL in
   `queries.py`, `db.py` pure, cache-then-serve, per-user isolation).

## Output

Exactly one file: `docs/specs/<feature>.md`. No code, no tests. `/implement` consumes it next.
