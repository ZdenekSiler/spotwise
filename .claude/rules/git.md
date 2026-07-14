# Git

- **Branches:** `feature/…`, `fix/…`, `chore/…`, `docs/…`. `main` is protected.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
  Small, focused, working. Commit only tested code.
- **PRs:** describe intent + how it was verified. Security-sensitive changes reference the
  `/security-review` result.
- **Secrets:** never commit `.env`, `secrets/`, `*.db`, or tokens. `detect-secrets` runs at
  pre-commit against `.secrets.baseline`; `route-auth-audit.py` runs at pre-push to `main`
  (every route must have an auth guard or be intentionally public).
- Install hooks once: `bash scripts/install-hooks.sh`.
- End commit messages with the co-author trailer when the change was AI-assisted.
