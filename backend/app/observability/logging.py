"""Structured JSON logging, request/correlation context, and redaction.

Logs are emitted as JSON to stdout and always carry ``request_id`` and
``correlation_id`` (when set). Sensitive structured fields are redacted by key
so secrets/PII never reach the logs (CLAUDE.md rule 14). Only an allow-listed
set of extra fields is ever serialized, so arbitrary sensitive extras are
dropped rather than logged.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Per-request context, set by RequestIdMiddleware and read by the formatter.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)

REDACTED = "***REDACTED***"

_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "cookie",
    "session",
    "ssn",
    "credit_card",
    "card_number",
    "cvv",
    "private_key",
    "access_token",
    "refresh_token",
    "jwt",
    "embedding",
    "vector",
)

# Extra fields permitted on a log record. Anything else is never serialized.
_EXTRA_FIELDS = (
    "event",
    "tenant_id",
    "actor_id",
    "job_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_code",
    "metadata",
)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def redact(value: Any) -> Any:
    """Recursively redact mapping values whose key looks sensitive."""
    if isinstance(value, dict):
        return {k: (REDACTED if _is_sensitive(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class JsonLogFormatter(logging.Formatter):
    """Render log records as a single-line JSON object with redaction."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self._service = service_name
        self._env = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._env,
            "request_id": request_id_ctx.get(),
            "correlation_id": correlation_id_ctx.get(),
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            val = getattr(record, field, None)
            if val is not None:
                payload[field] = val
        if record.exc_info and record.exc_info[0] is not None:
            # Type name only — never the traceback/locals, which may carry secrets.
            payload["exception"] = record.exc_info[0].__name__
        return json.dumps(redact(payload), default=str)


def setup_logging(settings: Any) -> logging.Logger:
    """Configure root logging to emit redacted JSON to stdout. Idempotent."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter(settings.service_name, settings.app_env))
    root.addHandler(handler)
    root.setLevel(getattr(logging, str(settings.log_level).upper(), logging.INFO))
    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
