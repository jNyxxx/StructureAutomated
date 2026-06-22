"""Health, liveness, and readiness endpoints.

- ``/health`` — process is up.
- ``/live``   — minimal liveness signal.
- ``/ready``  — readiness; DB/migration checks are wired in Slice 5, so until
  then this reports limited readiness (database ``not_configured``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.database import check_readiness

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/live")
async def live() -> dict[str, Any]:
    return {"status": "alive", "service": get_settings().service_name}


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    # Readiness checks DB connectivity + migration head when the DB is configured;
    # when it is not configured the API is still considered ready. check_readiness
    # never leaks the DSN, credentials, or raw driver errors.
    result = await check_readiness()
    if not result["ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if result["ready"] else "not_ready",
        "environment": get_settings().app_env,
        "checks": result["checks"],
    }
