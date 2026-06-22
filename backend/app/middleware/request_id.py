"""Request ID and correlation ID middleware.

Assigns a ``request_id`` to every request (respecting a valid inbound
``X-Request-ID``), derives a ``correlation_id`` (inbound ``X-Correlation-ID`` or
the request id), stores both on ``request.state`` and in context vars, and
echoes them on the response.
"""

from __future__ import annotations

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.logging import correlation_id_ctx, request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

# Accept only safe, bounded identifiers from clients.
_VALID_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def _sanitize(value: str | None) -> str | None:
    if value and _VALID_ID.match(value):
        return value
    return None


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _sanitize(request.headers.get(REQUEST_ID_HEADER)) or _generate_request_id()
        correlation_id = _sanitize(request.headers.get(CORRELATION_ID_HEADER)) or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        rid_token = request_id_ctx.set(request_id)
        cid_token = correlation_id_ctx.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(rid_token)
            correlation_id_ctx.reset(cid_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
