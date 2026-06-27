"""Redis rate-limit backend tests for P3-4c.

No live Redis server is required. The fake client emulates the atomic Lua script
contract that RedisRateLimitBackend uses: INCR, EXPIRE-on-first-hit, and TTL.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import _build_rate_limit_backend, create_app
from app.ratelimit.backend import InMemoryRateLimitBackend
from app.ratelimit.redis_backend import RedisRateLimitBackend
from app.services.rate_limit import RateLimitPolicy, RateLimitService

_NOW = datetime(2026, 6, 28, 12, 0, 0, tzinfo=UTC)


class _FailingBackend:
    async def incr(self, key: str, *, window: timedelta, now: datetime) -> tuple[int, int]:
        raise RuntimeError("redis://user:SENTINELPW@redis:6379/0 key=user@example.com")


class _FakeRedis:
    def __init__(self) -> None:
        self.now = 0
        self.calls: list[dict[str, Any]] = []
        self.store: dict[str, tuple[int, int]] = {}

    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> list[int]:
        del script
        assert numkeys == 1
        key = str(keys_and_args[0])
        window_seconds = int(keys_and_args[1])
        self.calls.append({"key": key, "window_seconds": window_seconds})

        expires_at, count = self.store.get(key, (0, 0))
        if expires_at <= self.now:
            expires_at, count = self.now + window_seconds, 0
        count += 1
        self.store[key] = (expires_at, count)
        return [count, expires_at - self.now]

    def advance(self, seconds: int) -> None:
        self.now += seconds


async def test_redis_backend_increments_and_returns_remaining_reset_values() -> None:
    fake = _FakeRedis()
    backend = RedisRateLimitBackend(fake)
    service = RateLimitService(backend)
    policy = RateLimitPolicy("redis", limit=2, window=timedelta(seconds=60))

    first = await service.check(policy, now=_NOW, tenant_id="tenant-1")
    second = await service.check(policy, now=_NOW, tenant_id="tenant-1")
    third = await service.check(policy, now=_NOW, tenant_id="tenant-1")

    assert first.allowed
    assert first.remaining == 1
    assert first.reset_after == 60
    assert second.allowed
    assert second.remaining == 0
    assert not third.allowed
    assert third.remaining == 0
    assert third.reset_after == 60


async def test_redis_backend_expires_and_resets_after_window() -> None:
    fake = _FakeRedis()
    backend = RedisRateLimitBackend(fake)
    service = RateLimitService(backend)
    policy = RateLimitPolicy("redis", limit=1, window=timedelta(seconds=30))

    first = await service.check(policy, now=_NOW, tenant_id="tenant-1")
    blocked = await service.check(policy, now=_NOW, tenant_id="tenant-1")
    fake.advance(31)
    after = await service.check(policy, now=_NOW + timedelta(seconds=31), tenant_id="tenant-1")

    assert first.allowed
    assert not blocked.allowed
    assert after.allowed
    assert after.remaining == 0
    assert after.reset_after == 30


def test_rate_limit_service_hashes_identifier_before_redis_storage() -> None:
    key = RateLimitService.build_key(
        "auth", ip="1.2.3.4", action="session", identifier="user@example.com"
    )

    assert "user@example.com" not in key
    assert "id=" in key
    assert key.startswith("rl:auth:")


async def test_redis_backend_receives_hashed_key_not_raw_identifier() -> None:
    fake = _FakeRedis()
    backend = RedisRateLimitBackend(fake)
    service = RateLimitService(backend)
    policy = RateLimitPolicy("auth", limit=10, window=timedelta(minutes=1))

    await service.check(
        policy,
        now=_NOW,
        ip="1.2.3.4",
        action="session",
        identifier="user@example.com",
    )

    stored_key = fake.calls[0]["key"]
    assert "user@example.com" not in stored_key
    assert "id=" in stored_key


def test_rate_limit_backend_builder_uses_in_memory_by_default() -> None:
    backend = _build_rate_limit_backend(Settings())

    assert isinstance(backend, InMemoryRateLimitBackend)


def test_rate_limit_backend_builder_uses_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = RedisRateLimitBackend(_FakeRedis())

    monkeypatch.setattr(
        RedisRateLimitBackend,
        "from_url",
        classmethod(lambda cls, url: sentinel),
    )

    backend = _build_rate_limit_backend(
        Settings(rate_limit_backend="redis", rate_limit_redis_url="redis://redis:6379/0")
    )

    assert backend is sentinel


def test_create_app_wires_in_memory_backend_by_default() -> None:
    get_settings.cache_clear()
    try:
        app = create_app()
        assert isinstance(app.state.rate_limit_backend, InMemoryRateLimitBackend)
        assert isinstance(app.state.rate_limit_service, RateLimitService)
    finally:
        get_settings.cache_clear()


def test_endpoint_rate_limit_backend_unavailable_returns_sanitized_503() -> None:
    app = create_app()
    app.state.rate_limit_service = RateLimitService(_FailingBackend())
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/auth/session")

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "RATE_LIMIT_BACKEND_UNAVAILABLE"
    assert body["error"]["message"] == "Rate limit backend unavailable."
    serialized = resp.text
    assert "SENTINELPW" not in serialized
    assert "user@example.com" not in serialized
    assert "redis://" not in serialized


def test_create_app_wires_redis_backend_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = RedisRateLimitBackend(_FakeRedis())

    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setattr(
        RedisRateLimitBackend,
        "from_url",
        classmethod(lambda cls, url: sentinel),
    )
    get_settings.cache_clear()
    try:
        app = create_app()
        assert app.state.rate_limit_backend is sentinel
        assert isinstance(app.state.rate_limit_service, RateLimitService)
    finally:
        get_settings.cache_clear()
