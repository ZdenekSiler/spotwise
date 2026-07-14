# Spec: Accounts & smart-meter consumption

Status: MVP. Owner modules: `auth.py`, `routers/consumption_api.py`.

## Accounts

Multi-user (per-user consumption data requires it). Argon2id password hashing; signed session
cookie (`itsdangerous.TimestampSigner`) carrying `user_id`; `Depends(current_user_id)` on
protected routes. Cookie: `HttpOnly`, `SameSite=Lax`, `Secure` in prod, 30-day Max-Age.
`ALLOW_SIGNUP` env toggle gates `/auth/signup` in prod.

- `POST /auth/signup` `{email, password}` → creates user, sets cookie. Rejects duplicate email.
- `POST /auth/login` `{email, password}` → verifies hash, sets cookie.
- `POST /auth/logout` → clears cookie.

## Consumption upload

`POST /api/consumption` (protected, `multipart/form-data`, CSV). Distributor exports vary;
accept the common shape: a timestamp column + a kWh column (15-min). Parse tolerantly
(delimiter `,`/`;`, decimal `.`/`,`, ISO or `DD.MM.YYYY HH:MM` timestamps). Upsert into
`consumption(user_id, ts, kwh)` — PK (`user_id`, `ts`), so re-upload is idempotent.

`GET /api/consumption?from=&to=` → user's 15-min series (isolated by `WHERE user_id = ?`).

## Isolation invariant

Every consumption/savings query filters `WHERE user_id = ?`. No cross-user read is possible
even with a guessed id. Enforced in `queries.py` (every consumption statement is parameterized
on user_id) and covered by an isolation test.

## Tests

`test_auth.py` (hash round-trip, cookie sign/verify, signup dup rejection, protected-route
401); `test_consumption.py` (CSV parse variants, idempotent upsert, per-user isolation).
