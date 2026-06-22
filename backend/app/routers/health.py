"""Health, liveness, and readiness endpoints.

- ``/health`` — process is up.
- ``/live``   — minimal liveness signal.
- ``/ready``  — readiness; DB/migration checks are wired in Slice 5, so until
  then this reports limited readiness (database ``not_configured``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/live")
async def live() -> dict[str, Any]:
    return {"status": "alive", "service": get_settings().service_name}


@router.get("/ready")
async def ready() -> dict[str, Any]:
    settings = get_settings()
    # Slice 5 replaces "not_configured" with a real DB + migration-head check.
    return {
        "status": "ok",
        "environment": settings.app_env,
        "checks": {"database": "not_configured"},
    }
