"""Exception handlers that render the standard error envelope.

All errors — application errors, HTTP exceptions, request-validation failures,
and unexpected exceptions — return the same envelope. Unexpected errors never
leak internals (no traceback, no exception message) to the client. Error
``details`` are redacted, and request-validation input values are dropped
entirely (they may contain secrets/PII).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.middleware.request_id import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from app.observability.logging import get_logger, redact
from app.schemas.errors import error_envelope

_logger = get_logger("app.error")

_HTTP_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


class AppError(Exception):
    """Raised by application code to return a controlled error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _ids(request: Request) -> tuple[str | None, str | None]:
    return (
        getattr(request.state, "request_id", None),
        getattr(request.state, "correlation_id", None),
    )


def _response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    correlation_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body = error_envelope(
        code=code, message=message, request_id=request_id, details=redact(details or {})
    )
    headers: dict[str, str] = {}
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    if correlation_id:
        headers[CORRELATION_ID_HEADER] = correlation_id
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id, correlation_id = _ids(request)
        _logger.warning(
            "app.error",
            extra={"event": "app.error", "status_code": exc.status_code, "error_code": exc.code},
        )
        return _response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            correlation_id=correlation_id,
            details=exc.details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id, correlation_id = _ids(request)
        code = _HTTP_CODE_BY_STATUS.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
        return _response(
            status_code=exc.status_code,
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id, correlation_id = _ids(request)
        # Drop the raw `input` (and `url`) — they may carry secrets/PII.
        safe_errors = [
            {"type": e.get("type"), "loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()
        ]
        return _response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=request_id,
            correlation_id=correlation_id,
            details={"errors": safe_errors},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        request_id, correlation_id = _ids(request)
        _logger.exception("unhandled.exception", extra={"event": "unhandled.exception"})
        return _response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id=request_id,
            correlation_id=correlation_id,
        )
