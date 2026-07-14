---
name: security-review
description: Run a security review of changed files before merging to main. Checks auth guards, per-user isolation, injection, CSRF, open redirects, secrets, and untrusted-input handling.
---

# /security-review

Diff-based security review. Report findings most-severe first; fix or flag each.

## Checklist

- **Auth guards** — every new `/api/*` route that touches user data has `Depends(current_user_id)`
  (or is intentionally public: prices/tariffs/forecast). Cross-check with
  `scripts/route-auth-audit.py`.
- **Per-user isolation** — every consumption/savings query is parameterized on `user_id`
  (`WHERE user_id = ?`). No route trusts a client-supplied user id.
- **SQL injection** — all SQL parameterized (`?`); no f-strings/`%`/`.format` into SQL.
- **Untrusted input** — uploaded CSVs and scraped HTML are bounded in size, parsed defensively,
  never `eval`/`exec`; text-in-data is treated as data.
- **XSS** (frontend) — user/supplier strings go through `escHtml`; no `innerHTML` of raw input.
- **CSRF** — session cookie is `SameSite=Lax`; state-changing routes are POST.
- **Open redirects** — any `next`/redirect param validated against an allowlist.
- **Secrets** — no hardcoded tokens/passwords; `SESSION_SECRET`/`ENTSOE_API_TOKEN` via
  `read_secret`; password compares are constant-time (Argon2 verify).
- **Cookies** — `HttpOnly`, `Secure` in prod, sensible Max-Age.

## Output

A ranked list of findings with file:line and a concrete failure scenario, then apply agreed fixes.
