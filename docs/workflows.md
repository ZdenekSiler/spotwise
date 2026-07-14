# Workflows

The development loop mirrors the reference projects: **design before code**, specs in
`docs/specs/`, parallel subagents for implementation, quality + security review before commit.

```
  /design  ──►  docs/specs/<feature>.md   (Explore agents research → written spec)
     │
     ▼
  /implement  ──►  code + tests            (decompose spec → parallel subagents;
     │                                       main.py / services/db.py / queries.py /
     │                                       conftest.py reserved for the coordinator)
     ▼
  /simplify   ──►  dedup, remove single-use abstractions, project checks
     │             (e.g. all SQL in queries.py; clients stay thin; fusion stays pure)
     ▼
  make test   ──►  uv run pytest -x -q     (real SQLite per test, respx-mocked HTTP)
     │
     ▼
  /security-review  ──►  auth guards, XSS, SQLi, CSRF, open redirects, secrets
     │
     ▼
  git commit (Conventional Commits)  ──►  /deploy dev|prod
```

## Key principles

- Always `/design` before `/implement` for any non-trivial change.
- Keep `CLAUDE.md` < 200 lines; it links out to `docs/` and `.claude/rules/`.
- Commit only working, tested code. Every route has an auth guard or is intentionally public
  (`scripts/route-auth-audit.py` enforces this at pre-push).
- New code ≥80% coverage; pure utils (fusion math) 100%.
