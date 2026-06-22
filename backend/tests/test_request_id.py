"""Request ID / correlation ID generation and propagation tests (Slice 3)."""

import re

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

_GENERATED = re.compile(r"^req_[0-9a-f]{32}$")


def test_request_id_generated_when_absent() -> None:
    resp = client.get("/health")
    request_id = resp.headers["X-Request-ID"]
    assert _GENERATED.match(request_id)
    # Correlation id defaults to the request id when none is supplied.
    assert resp.headers["X-Correlation-ID"] == request_id


def test_valid_inbound_request_id_is_respected() -> None:
    resp = client.get("/health", headers={"X-Request-ID": "req_custom-123"})
    assert resp.headers["X-Request-ID"] == "req_custom-123"


def test_invalid_inbound_request_id_is_replaced() -> None:
    resp = client.get("/health", headers={"X-Request-ID": "bad id with spaces!"})
    assert resp.headers["X-Request-ID"] != "bad id with spaces!"
    assert resp.headers["X-Request-ID"].startswith("req_")


def test_correlation_id_propagates_independently() -> None:
    resp = client.get("/health", headers={"X-Correlation-ID": "corr-abc"})
    assert resp.headers["X-Correlation-ID"] == "corr-abc"
    assert resp.headers["X-Request-ID"].startswith("req_")
