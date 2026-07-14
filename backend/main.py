"""Spotwise FastAPI application.

Entry point: lifespan (init_db + APScheduler), auth routes, router mounts, /health. Route
handlers live in routers/*; this file only wires the app and holds cross-cutting concerns.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import auth
import config
from rate_limit import limiter
from routers import (
    consumption_api,
    forecast_api,
    prices_api,
    savings_api,
    tariffs_api,
    user_api,
)
from services import db, scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("spotwise")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast in production if the session secret is missing/weak.
    secret = config.read_secret("spotwise_session_secret", "SESSION_SECRET")
    if config.is_production() and (not secret or len(secret) < 32):
        log.error("SESSION_SECRET missing or < 32 chars — refusing to start in production")
        sys.exit(1)

    await db.init_db()
    scheduler.start()
    log.info("Spotwise started (production=%s)", config.is_production())
    try:
        yield
    finally:
        scheduler.shutdown()


def create_app() -> FastAPI:
    docs_url = None if config.is_production() else "/api/docs"
    app = FastAPI(title="Spotwise", version="0.1.0", lifespan=lifespan,
                  docs_url=docs_url, redoc_url=None)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.allowed_origin()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(prices_api.router)
    app.include_router(tariffs_api.router)
    app.include_router(consumption_api.router)
    app.include_router(savings_api.router)
    app.include_router(forecast_api.router)
    app.include_router(user_api.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def _rate_limit_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=429, content={"detail": "Příliš mnoho požadavků"})


app = create_app()
