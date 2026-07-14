"""Authentication: hashing, signup/login, session guard."""

from __future__ import annotations

import auth


def test_hash_and_verify_password_roundtrip():
    h = auth.hash_password("password123")
    assert h != "password123"
    assert auth.verify_password(h, "password123") is True
    assert auth.verify_password(h, "wrong") is False


async def test_signup_sets_session_cookie(client):
    resp = await client.post("/auth/signup", json={"email": "a@b.cz", "password": "password123"})
    assert resp.status_code == 200
    assert auth.COOKIE_NAME in resp.cookies


async def test_signup_duplicate_email_conflicts(client):
    body = {"email": "dup@b.cz", "password": "password123"}
    await client.post("/auth/signup", json=body)
    resp = await client.post("/auth/signup", json=body)
    assert resp.status_code == 409


async def test_login_rejects_bad_password(client):
    await client.post("/auth/signup", json={"email": "c@b.cz", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "c@b.cz", "password": "wrongpassword"})
    assert resp.status_code == 401


async def test_protected_route_requires_session(client):
    resp = await client.get("/api/consumption")
    assert resp.status_code == 401


async def test_me_returns_current_user(auth_client):
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"
