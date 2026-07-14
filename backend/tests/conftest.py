"""Shared test fixtures.

Convention: no DB mocking — each test hits a real SQLite DB in a tmp path (schema + migrations
+ seed run for real). External HTTP is mocked with respx per-test. HTTP via httpx ASGITransport
(no lifespan; the fixture inits the DB directly, avoiding the background scheduler).
"""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio

# A test session secret (≥32 chars) so auth cookie signing works.
os.environ.setdefault("SESSION_SECRET", "x" * 48)
os.environ.setdefault("ALLOWED_ORIGIN", "*")


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))


@pytest_asyncio.fixture
async def app():
    # Import after env is set so config picks up the tmp DB path.
    import config
    from services import db

    monkey_path = config.db_path()  # noqa: F841 — force evaluation
    await db.init_db()

    import main
    return main.create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client):
    resp = await client.post(
        "/auth/signup", json={"email": "user@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    return client
