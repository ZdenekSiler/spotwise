"""Multi-user authentication: Argon2id hashing + signed session cookie.

Session = a signed cookie carrying the user id (itsdangerous). Protected routes depend on
current_user_id. Per-user data isolation is enforced at the SQL layer (WHERE user_id = ?).
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, TimestampSigner
from pydantic import BaseModel, EmailStr, Field

import config
from services import db

COOKIE_NAME = "spotwise_session"
_MAX_AGE = 30 * 24 * 3600  # 30 days

# Lean Argon2id params (OWASP minimum: 19 MiB, t=2, p=1). The library defaults (64 MiB, p=4)
# are sized for many-core servers and would spike a shared-vCPU host under a login burst.
_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)
router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Models ───

class CredentialsIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


# ─── Hashing ───

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# ─── Session cookie ───

def _signer() -> TimestampSigner:
    secret = config.read_secret("spotwise_session_secret", "SESSION_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("SESSION_SECRET missing or shorter than 32 chars")
    return TimestampSigner(secret)


def _set_session(response: Response, user_id: int) -> None:
    token = _signer().sign(str(user_id).encode()).decode()
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=_MAX_AGE, httponly=True, samesite="lax",
        secure=config.is_production(), path="/",
    )


def _read_session(request: Request) -> int | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        value = _signer().unsign(raw, max_age=_MAX_AGE)
        return int(value.decode())
    except (BadSignature, ValueError):
        return None


async def current_user_id(request: Request) -> int:
    """Dependency for protected routes. 401 if no valid session."""
    user_id = _read_session(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Přihlaste se prosím")
    return user_id


# ─── Routes ───

@router.post("/signup")
async def signup(creds: CredentialsIn, response: Response):
    if not config.allow_signup():
        raise HTTPException(status_code=403, detail="Registrace je momentálně uzavřená")
    try:
        user_id = await db.create_user(creds.email, hash_password(creds.password))
    except ValueError:
        raise HTTPException(status_code=409, detail="E-mail je již registrován")
    _set_session(response, user_id)
    return {"id": user_id, "email": creds.email}


@router.post("/login")
async def login(creds: CredentialsIn, response: Response):
    user = await db.get_user_by_email(creds.email)
    if user is None or not verify_password(user["password_hash"], creds.password):
        raise HTTPException(status_code=401, detail="Neplatné přihlašovací údaje")
    _set_session(response, user["id"])
    return {"id": user["id"], "email": user["email"]}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user_id: int = Depends(current_user_id)):
    return await db.get_user(user_id)
