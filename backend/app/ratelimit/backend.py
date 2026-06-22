"""Rate-limit counter backends.

``RateLimitBackend`` is the production-shaped interface; ``InMemoryRateLimitBackend``
is the local/dev/test adapter (fixed-window counters, single process). A shared
store (Redis/Postgres) can implement the same protocol for multi-process use.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Protocol


class RateLimitBackend(Protocol):
    async def incr(self, key: str, *, window: timedelta, now: datetime) -> tuple[int, int]:
        """Count one hit for ``key`` in its current window.

        Returns ``(count_in_window, reset_after_seconds)``.
        """
        ...


class InMemoryRateLimitBackend:
    """Fixed-window counters held in process memory. Not shared across workers."""

    def __init__(self) -> None:
        self._windows: dict[str, tuple[datetime, int]] = {}

    async def incr(self, key: str, *, window: timedelta, now: datetime) -> tuple[int, int]:
        start, count = self._windows.get(key, (now, 0))
        if now - start >= window:
            start, count = now, 0
        count += 1
        self._windows[key] = (start, count)
        reset_after = max(0, math.ceil((start + window - now).total_seconds()))
        return count, reset_after
