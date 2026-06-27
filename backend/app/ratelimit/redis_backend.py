"""Redis-backed rate-limit counter backend.

This backend implements the same fixed-window ``RateLimitBackend`` protocol as
the local in-memory adapter, but stores counters in Redis so limits are shared
across API workers and processes. The Redis client import is intentionally lazy:
local/test environments can keep using the in-memory backend without requiring a
live Redis server.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable
from datetime import datetime, timedelta
from typing import Protocol


class RedisClient(Protocol):
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


class RedisRateLimitBackend:
    """Fixed-window Redis counter backend using one atomic Lua script per hit."""

    _INCR_EXPIRE_TTL_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""

    def __init__(self, client: RedisClient) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> RedisRateLimitBackend:
        """Build from a Redis URL, importing redis.asyncio only when selected."""
        try:
            from redis.asyncio import Redis
        except ImportError as exc:  # pragma: no cover - exercised by deployment config
            raise RuntimeError("redis package is required when RATE_LIMIT_BACKEND=redis") from exc
        return cls(Redis.from_url(url, decode_responses=False))

    async def incr(self, key: str, *, window: timedelta, now: datetime) -> tuple[int, int]:
        """Count one hit in Redis and return ``(count, reset_after_seconds)``.

        ``now`` is accepted for protocol compatibility; Redis owns TTL time for
        the distributed counter. Key construction remains owned by
        ``RateLimitService``, which hashes free-text identifiers before storage.
        """
        del now
        window_seconds = max(1, math.ceil(window.total_seconds()))
        raw = await self._eval(self._INCR_EXPIRE_TTL_SCRIPT, 1, key, window_seconds)
        count, ttl = _parse_redis_pair(raw)
        return count, max(0, ttl)

    async def _eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        result = self._client.eval(script, numkeys, *keys_and_args)
        if isinstance(result, Awaitable):
            return await result
        return result


def _parse_redis_pair(raw: object) -> tuple[int, int]:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        return int(raw[0]), int(raw[1])
    raise TypeError("Redis rate-limit script returned an unexpected shape")
