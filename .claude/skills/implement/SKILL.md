---
name: implement
description: Implement a feature from its design spec in docs/specs/<feature>.md. Decomposes the spec into independent tasks and runs parallel subagents for fast delivery. Always run /design first.
argument-hint: <feature name matching docs/specs/<feature>.md>
---

# /implement

Turn a spec in `docs/specs/<feature>.md` into working, tested code.

## Steps

1. Read the spec. If it is missing, stop and tell the user to run `/design` first.
2. Decompose into **independent** tasks (a client, a fusion function, a router, its tests).
3. Run parallel subagents for the independent pieces. **Reserve for the coordinator** (do not
   let subagents edit these concurrently): `backend/main.py`, `backend/services/db.py`,
   `backend/services/queries.py`, `backend/tests/conftest.py` — these are shared and must be
   merged carefully.
4. Enforce the invariants in `.claude/rules/architecture.md`: thin clients, all SQL in
   `queries.py`, `db.py` never imports `fastapi`, fusion stays pure, cache-then-serve, per-user
   isolation, `*In`/`*Out` + `HTTPException`.
5. Add `test_<module>.py` per new module (real SQLite per test, `respx` for HTTP) —
   see `.claude/rules/testing.md`. Pure fusion utils get 100% coverage.
6. Run `make test` (`uv run pytest -x -q`) until green.

## After

Suggest `/simplify` then `/security-review` before committing.
