# Testing

- **Stack:** pytest + pytest-asyncio (`asyncio_mode = "auto"`), FastAPI `TestClient`/httpx,
  `respx` for mocking external HTTP, `pytest-playwright` for e2e (skipped without a live server).
- **Layout:** one `test_<module>.py` per source module. Names:
  `test_<function>_<condition>_<expected>`. AAA structure (arrange/act/assert).
- **No DB mocking.** Each test hits a **real SQLite** DB injected via an `autouse` fixture that
  `monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))` (or monkeypatches `db.DB_PATH`),
  then runs `init_db()`. Tests exercise the real schema + migrations.
- **No live external calls.** Mock OTE/ENTSO-E/Open-Meteo/ČNB HTTP with `respx`. Assert the
  degradation paths (missing token, network error) never raise.
- **Fixtures:** `client` (unauthenticated), `auth_client` (signed-up + logged-in user) in
  `conftest.py`.
- **Coverage gates:** ≥80% for new code; **100% for pure fusion utils** (`landed_cost`,
  `forecast`, savings math) — they are the correctness core.
- Run: `make test` or `cd backend && uv run pytest -x -q`.
