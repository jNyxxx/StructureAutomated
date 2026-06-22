"""Structured logging and redaction tests (Slice 3)."""

import json
import logging

from app.observability.logging import (
    REDACTED,
    JsonLogFormatter,
    correlation_id_ctx,
    redact,
    request_id_ctx,
)


def test_redact_scrubs_sensitive_keys_recursively() -> None:
    data = {
        "password": "p@ss",
        "api_key": "sk_live_xxx",
        "nested": {"refresh_token": "t", "ok": "keep"},
        "items": [{"secret": "s"}, {"plain": "v"}],
    }
    out = redact(data)
    assert out["password"] == REDACTED
    assert out["api_key"] == REDACTED
    assert out["nested"]["refresh_token"] == REDACTED
    assert out["nested"]["ok"] == "keep"
    assert out["items"][0]["secret"] == REDACTED
    assert out["items"][1]["plain"] == "v"


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_emits_json_with_request_context() -> None:
    rid = request_id_ctx.set("req_test123")
    cid = correlation_id_ctx.set("corr_test")
    try:
        line = JsonLogFormatter("backend", "local").format(_record(event="something"))
    finally:
        request_id_ctx.reset(rid)
        correlation_id_ctx.reset(cid)
    obj = json.loads(line)
    assert obj["request_id"] == "req_test123"
    assert obj["correlation_id"] == "corr_test"
    assert obj["service"] == "backend"
    assert obj["environment"] == "local"
    assert obj["level"] == "INFO"
    assert obj["event"] == "something"


def test_formatter_redacts_sensitive_metadata() -> None:
    line = JsonLogFormatter("backend", "local").format(
        _record(metadata={"password": "SENTINELSECRET", "ok": "v"})
    )
    obj = json.loads(line)
    assert obj["metadata"]["password"] == REDACTED
    assert obj["metadata"]["ok"] == "v"
    assert "SENTINELSECRET" not in line
