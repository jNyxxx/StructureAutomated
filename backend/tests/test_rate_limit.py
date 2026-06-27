"""Rate-limit foundation tests (Slice 12).

Deterministic service/throttle tests use an injected ``now`` and the in-memory
backend; middleware tests drive a tiny app through TestClient. No PII appears in
counter keys (free-text identifiers such as email are hashed).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.error_handler import AppError
from app.middleware.rate_limit import RateLimitMiddleware
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.services.rate_limit import (
    DEFAULT_POLICIES,
    RateLimitExceeded,
    RateLimitPolicy,
    RateLimitService,
)
from app.workers.throttle import JobThrottle

_NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=UTC)


def _service() -> RateLimitService:
    return RateLimitService(InMemoryRateLimitBackend())


async def test_allows_up_to_limit_then_blocks() -> None:
    svc = _service()
    policy = RateLimitPolicy("test", limit=3, window=timedelta(minutes=1))

    results = [await svc.check(policy, now=_NOW, ip="1.1.1.1") for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[0].remaining == 2
    assert results[-1].remaining == 0
    assert results[-1].retry_after > 0


async def test_window_resets_after_elapsed() -> None:
    svc = _service()
    policy = RateLimitPolicy("test", limit=1, window=timedelta(minutes=1))

    first = await svc.check(policy, now=_NOW, ip="1.1.1.1")
    blocked = await svc.check(policy, now=_NOW + timedelta(seconds=10), ip="1.1.1.1")
    after = await svc.check(policy, now=_NOW + timedelta(minutes=2), ip="1.1.1.1")

    assert first.allowed
    assert not blocked.allowed
    assert after.allowed  # new window


def test_keys_separate_by_dimension_and_hash_identifier() -> None:
    k_ip = RateLimitService.build_key("auth", ip="1.2.3.4")
    k_tenant = RateLimitService.build_key("risky", tenant_id="tenant-123")
    k_action = RateLimitService.build_key("risky", tenant_id="tenant-123", action="import")

    # Distinct scopes → distinct keys.
    assert len({k_ip, k_tenant, k_action}) == 3

    k_email = RateLimitService.build_key("auth", ip="1.2.3.4", identifier="user@example.com")
    # Free-text identifier (email = PII) is hashed, never stored raw.
    assert "user@example.com" not in k_email
    # Structural dimensions stay readable.
    assert "1.2.3.4" in k_email
    assert "auth" in k_email
    # Stable for the same identifier; different identifiers differ.
    assert k_email == RateLimitService.build_key(
        "auth", ip="1.2.3.4", identifier="user@example.com"
    )
    assert k_email != RateLimitService.build_key(
        "auth", ip="1.2.3.4", identifier="other@example.com"
    )


async def test_enforce_raises_rate_limited_app_error() -> None:
    svc = _service()
    policy = RateLimitPolicy("test", limit=1, window=timedelta(minutes=1))

    await svc.enforce(policy, now=_NOW, tenant_id="tenant-1")
    with pytest.raises(RateLimitExceeded) as excinfo:
        await svc.enforce(policy, now=_NOW, tenant_id="tenant-1")

    exc = excinfo.value
    # Standard envelope path, not a raw 500: RateLimitExceeded is an AppError.
    assert isinstance(exc, AppError)
    assert exc.code == "RATE_LIMITED"
    assert exc.status_code == 429
    assert exc.result.retry_after > 0


def test_default_policies_cover_auth_webhook_import_risky_and_job() -> None:
    for name in ("auth", "webhook", "import", "risky_action", "job"):
        assert name in DEFAULT_POLICIES
        assert DEFAULT_POLICIES[name].limit > 0
        assert DEFAULT_POLICIES[name].window.total_seconds() > 0
    assert DEFAULT_POLICIES["import"].limit == 10
    assert DEFAULT_POLICIES["import"].window == timedelta(minutes=5)


async def test_shared_backend_persists_counter_across_service_instances() -> None:
    backend = InMemoryRateLimitBackend()
    svc_one = RateLimitService(backend)
    svc_two = RateLimitService(backend)
    policy = RateLimitPolicy("shared", limit=1, window=timedelta(minutes=1))

    first = await svc_one.check(policy, now=_NOW, tenant_id="tenant-1")
    second = await svc_two.check(policy, now=_NOW, tenant_id="tenant-1")

    assert first.allowed
    assert not second.allowed


async def test_job_throttle_is_scoped_per_tenant_and_job_type() -> None:
    svc = _service()
    throttle = JobThrottle(svc, RateLimitPolicy("job", limit=1, window=timedelta(minutes=1)))

    a1 = await throttle.allow(tenant_id="tenant-A", job_type="import", now=_NOW)
    a2 = await throttle.allow(tenant_id="tenant-A", job_type="import", now=_NOW)
    b1 = await throttle.allow(tenant_id="tenant-B", job_type="import", now=_NOW)
    c1 = await throttle.allow(tenant_id="tenant-A", job_type="send", now=_NOW)

    assert a1.allowed
    assert not a2.allowed  # same tenant + job type → capped
    assert b1.allowed  # different tenant → independent
    assert c1.allowed  # different job type → independent


def _mw_app(*, enabled: bool = True, limit: int = 2) -> FastAPI:
    app = FastAPI()
    service = RateLimitService(InMemoryRateLimitBackend())
    policy = RateLimitPolicy("ip", limit=limit, window=timedelta(minutes=1))
    app.add_middleware(RateLimitMiddleware, service=service, policy=policy, enabled=enabled)

    @app.get("/ping")
    async def _ping() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_middleware_over_limit_returns_envelope_with_headers() -> None:
    client = TestClient(_mw_app(enabled=True, limit=2), raise_server_exceptions=False)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    resp = client.get("/ping")  # third request exceeds the limit

    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert set(body["error"].keys()) == {"code", "message", "details", "request_id"}
    assert resp.headers["RateLimit-Limit"] == "2"
    assert "RateLimit-Remaining" in resp.headers
    assert "RateLimit-Reset" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


def test_middleware_under_limit_passes_with_headers() -> None:
    client = TestClient(_mw_app(enabled=True, limit=5), raise_server_exceptions=False)

    resp = client.get("/ping")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert resp.headers["RateLimit-Limit"] == "5"
    assert int(resp.headers["RateLimit-Remaining"]) == 4


def test_middleware_disabled_is_passthrough() -> None:
    client = TestClient(_mw_app(enabled=False, limit=1), raise_server_exceptions=False)

    first = client.get("/ping")
    second = client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 200  # not limited when disabled
    assert "RateLimit-Limit" not in first.headers
