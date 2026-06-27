"""Rate-limit service: policies, key building, and over-limit enforcement.

Keys combine the scope dimensions the API contract calls for (per-IP,
per-tenant, per-endpoint/action, per-job-type — see API_CONTRACT §6). Structural
dimensions (policy name, IP, tenant id, action, job type) stay readable; any
free-text ``identifier`` (e.g. an email for auth IP+email limiting) is hashed so
**no PII lands in a counter key** (CLAUDE.md rule 14).

Over-limit raises ``RateLimitExceeded`` — an ``AppError`` — so callers return the
standard error envelope (code ``RATE_LIMITED``, HTTP 429), never a raw 500.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.middleware.error_handler import AppError
from app.ratelimit.backend import RateLimitBackend


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window: timedelta


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_after: int  # seconds until the current window resets

    @property
    def retry_after(self) -> int:
        return 0 if self.allowed else self.reset_after


class RateLimitExceeded(AppError):
    """Raised when a rate-limit check is over the limit."""

    def __init__(self, result: RateLimitResult) -> None:
        super().__init__(
            "RATE_LIMITED",
            "Rate limit exceeded.",
            status_code=429,
            details={"limit": result.limit, "retry_after": result.retry_after},
        )
        self.result = result


def _hash_identifier(value: str) -> str:
    # Truncated SHA-256 — enough entropy to separate identifiers without storing PII.
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class RateLimitService:
    def __init__(self, backend: RateLimitBackend) -> None:
        self._backend = backend

    @staticmethod
    def build_key(
        policy_name: str,
        *,
        ip: str | None = None,
        tenant_id: str | None = None,
        action: str | None = None,
        job_type: str | None = None,
        identifier: str | None = None,
    ) -> str:
        parts = [f"rl:{policy_name}"]
        if ip is not None:
            parts.append(f"ip={ip}")
        if tenant_id is not None:
            parts.append(f"t={tenant_id}")
        if action is not None:
            parts.append(f"a={action}")
        if job_type is not None:
            parts.append(f"j={job_type}")
        if identifier is not None:
            parts.append(f"id={_hash_identifier(identifier)}")
        return ":".join(parts)

    async def check(
        self,
        policy: RateLimitPolicy,
        *,
        now: datetime,
        ip: str | None = None,
        tenant_id: str | None = None,
        action: str | None = None,
        job_type: str | None = None,
        identifier: str | None = None,
    ) -> RateLimitResult:
        key = self.build_key(
            policy.name,
            ip=ip,
            tenant_id=tenant_id,
            action=action,
            job_type=job_type,
            identifier=identifier,
        )
        count, reset_after = await self._backend.incr(key, window=policy.window, now=now)
        return RateLimitResult(
            allowed=count <= policy.limit,
            limit=policy.limit,
            remaining=max(0, policy.limit - count),
            reset_after=reset_after,
        )

    async def enforce(
        self,
        policy: RateLimitPolicy,
        *,
        now: datetime,
        ip: str | None = None,
        tenant_id: str | None = None,
        action: str | None = None,
        job_type: str | None = None,
        identifier: str | None = None,
    ) -> RateLimitResult:
        result = await self.check(
            policy,
            now=now,
            ip=ip,
            tenant_id=tenant_id,
            action=action,
            job_type=job_type,
            identifier=identifier,
        )
        if not result.allowed:
            raise RateLimitExceeded(result)
        return result


# Foundation defaults. Per-endpoint tuning lands with each route/worker slice;
# these are conservative per-minute baselines for the contract's scopes.
DEFAULT_POLICIES: dict[str, RateLimitPolicy] = {
    "auth": RateLimitPolicy("auth", limit=10, window=timedelta(minutes=1)),
    "webhook": RateLimitPolicy("webhook", limit=120, window=timedelta(minutes=1)),
    "import": RateLimitPolicy("import", limit=10, window=timedelta(minutes=5)),
    "risky_action": RateLimitPolicy("risky_action", limit=30, window=timedelta(minutes=1)),
    "job": RateLimitPolicy("job", limit=60, window=timedelta(minutes=1)),
}
