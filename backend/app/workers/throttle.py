"""Job throttle foundation for workers (per-tenant / per-job-type caps).

Workers reuse the same ``RateLimitService`` and counter backend as routes
(CLAUDE.md layer rules) — this is a thin, job-scoped wrapper. Real workers set
tenant context before any tenant query; the throttle key is the tenant id +
job type only (no PII).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.services.rate_limit import RateLimitPolicy, RateLimitResult, RateLimitService


class JobThrottle:
    def __init__(self, service: RateLimitService, policy: RateLimitPolicy) -> None:
        self._service = service
        self._policy = policy

    async def allow(
        self, *, tenant_id: uuid.UUID | str, job_type: str, now: datetime
    ) -> RateLimitResult:
        """Count one job attempt for (tenant, job_type); caller skips/defers if not allowed."""
        return await self._service.check(
            self._policy, now=now, tenant_id=str(tenant_id), job_type=job_type
        )
