"""Baseline per-IP rate-limit middleware.

A foundation guard: when enabled, it applies one per-IP policy to every request
and, on over-limit, returns the **standard error envelope** (code
``RATE_LIMITED``, HTTP 429) with ``RateLimit-*`` and ``Retry-After`` headers —
never a raw 500. Per-endpoint / per-tenant / per-action limits are applied in
routes via ``RateLimitService.enforce`` as those endpoints land.

Disabled by default (``enabled=False``) so it is a pure pass-through until a
deployment opts in; the envelope is built here directly because middleware-level
exceptions do not flow through the app's exception handlers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.schemas.errors import error_envelope
from app.services.rate_limit import RateLimitPolicy, RateLimitResult, RateLimitService


def _apply_headers(response: Response, result: RateLimitResult) -> None:
    response.headers["RateLimit-Limit"] = str(result.limit)
    response.headers["RateLimit-Remaining"] = str(result.remaining)
    response.headers["RateLimit-Reset"] = str(result.reset_after)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        service: RateLimitService,
        policy: RateLimitPolicy,
        enabled: bool,
    ) -> None:
        super().__init__(app)
        self._service = service
        self._policy = policy
        self._enabled = enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._enabled:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        result = await self._service.check(self._policy, now=datetime.now(UTC), ip=ip)

        if not result.allowed:
            request_id = getattr(request.state, "request_id", None)
            body = error_envelope(
                code="RATE_LIMITED",
                message="Rate limit exceeded.",
                request_id=request_id,
                details={"retry_after": result.retry_after},
            )
            response: Response = JSONResponse(status_code=429, content=body)
            response.headers["Retry-After"] = str(result.retry_after)
            _apply_headers(response, result)
            return response

        response = await call_next(request)
        _apply_headers(response, result)
        return response
