"""FastAPI application entrypoint.

Wires the Slice 3 backend foundation: environment-aware config, structured JSON
logging, request/correlation IDs, the standard error envelope, and the
health/live/ready endpoints. No DB, auth, billing, queue, or provider logic is
present yet — those arrive in later slices.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from app.config import get_settings
from app.database import get_engine
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.observability.boot_guard import BootGuardError, database_failures, enforce_config
from app.observability.logging import setup_logging
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.routers import (
    auth,
    campaigns,
    contacts,
    deliverability,
    drafts,
    followups,
    health,
    imports,
    outcomes,
    review,
    sending,
)
from app.services.rate_limit import RateLimitPolicy, RateLimitService


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    enforce_config(settings)  # production-gated config guard (no-op otherwise)
    if settings.is_production and settings.is_db_configured:
        async with get_engine().connect() as conn:
            failures = await database_failures(conn, settings)
            if failures:
                raise BootGuardError(failures)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)

    app = FastAPI(title="AutomatedStructure API", version="0.0.0", lifespan=_lifespan)

    # Added last = outermost. RequestIdMiddleware must wrap the others so that
    # request/correlation context (and request_id for the rate-limit envelope)
    # is set before they run.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        service=RateLimitService(InMemoryRateLimitBackend()),
        policy=RateLimitPolicy(
            "ip",
            limit=settings.rate_limit_default_limit,
            window=timedelta(seconds=settings.rate_limit_window_seconds),
        ),
        enabled=settings.rate_limit_enabled,
    )
    app.add_middleware(RequestIdMiddleware)

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(imports.router)
    app.include_router(contacts.router)
    app.include_router(campaigns.router)
    app.include_router(drafts.router)
    app.include_router(review.router)
    app.include_router(sending.router)
    app.include_router(followups.router)
    app.include_router(deliverability.router)
    app.include_router(outcomes.router)
    return app


app = create_app()
