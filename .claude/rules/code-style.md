# Code style

No formatter/linter is configured beyond security tooling; style is convention-enforced.

## Python (backend)

- 4-space indent, double quotes, full type hints on public functions.
- `snake_case` functions/vars, `PascalCase` for Pydantic models/classes, `_`-prefixed private
  helpers.
- Section dividers: `# ─── Section ───`.
- Pydantic v2: `*In` for request bodies, `*Out` for responses; `ConfigDict(extra="ignore")`.
- Errors on API paths: `raise HTTPException(status_code=..., detail=...)`. Data layer raises
  `ValueError`.
- Async everywhere in the request path (`aiosqlite`, `httpx.AsyncClient`).
- Comments explain **why**, not what. No commented-out code.

## JavaScript (frontend)

- 2-space indent, semicolons, `camelCase`.
- Each module is an IIFE exposing only what other modules need via `window`
  (`apiFetch`, `escHtml`, `fmtNum`, …). No framework, no build step.
- Prefer small pure helpers; keep DOM glue at the edges.
- Czech-localized user-facing strings.

## SQL

- One named constant per statement in `queries.py`, grouped by table in sections mirroring
  `db.py`. Parameterized (`?`) always — never string-format values into SQL.
