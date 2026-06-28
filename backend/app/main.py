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

from app.auth.clerk_jwks import build_managed_clerk_verifier
from app.auth.local_mock import build_local_mock_auth_service
from app.auth.managed import is_managed_auth_configured
from app.config import Settings, get_settings
from app.database import get_engine
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.observability.boot_guard import BootGuardError, database_failures, enforce_config
from app.observability.logging import setup_logging
from app.ratelimit.backend import InMemoryRateLimitBackend, RateLimitBackend
from app.ratelimit.redis_backend import RedisRateLimitBackend
from app.routers import (
    auth,
    billing,
    campaigns,
    compliance,
    contacts,
    deliverability,
    drafts,
    followups,
    health,
    imports,
    outcomes,
    review,
    sending,
    webhooks,
)
from app.routers import settings as settings_router
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


def _build_rate_limit_backend(settings: Settings) -> RateLimitBackend:
    backend = settings.rate_limit_backend.strip().lower()
    if backend == "in_memory":
        return InMemoryRateLimitBackend()
    if backend == "redis":
        if not settings.rate_limit_redis_url:
            raise RuntimeError("RATE_LIMIT_REDIS_URL is required when RATE_LIMIT_BACKEND=redis")
        return RedisRateLimitBackend.from_url(settings.rate_limit_redis_url)
    raise RuntimeError(f"Unsupported RATE_LIMIT_BACKEND '{settings.rate_limit_backend}'")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)

    app = FastAPI(title="AutomatedStructure API", version="0.0.0", lifespan=_lifespan)

    rate_limit_backend = _build_rate_limit_backend(settings)
    rate_limit_service = RateLimitService(rate_limit_backend)
    app.state.rate_limit_backend = rate_limit_backend
    app.state.rate_limit_service = rate_limit_service

    # Added last = outermost. RequestIdMiddleware must wrap the others so that
    # request/correlation context (and request_id for the rate-limit envelope)
    # is set before they run.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        service=rate_limit_service,
        policy=RateLimitPolicy(
            "ip",
            limit=settings.rate_limit_default_limit,
            window=timedelta(seconds=settings.rate_limit_window_seconds),
        ),
        enabled=settings.rate_limit_enabled,
    )
    app.add_middleware(RequestIdMiddleware)

    if not settings.is_production and settings.mock_verifier:
        app.state.auth_service = build_local_mock_auth_service()
    elif settings.auth_provider == "managed" and is_managed_auth_configured(settings):
        app.state.clerk_verifier = build_managed_clerk_verifier(settings)

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(billing.router)
    app.include_router(imports.router)
    app.include_router(contacts.router)
    app.include_router(campaigns.router)
    app.include_router(compliance.router)
    app.include_router(drafts.router)
    app.include_router(review.router)
    app.include_router(sending.router)
    app.include_router(settings_router.router)
    app.include_router(followups.router)
    app.include_router(deliverability.router)
    app.include_router(outcomes.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
