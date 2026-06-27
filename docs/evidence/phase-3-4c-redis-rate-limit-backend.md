# P3-4c — Redis RateLimitBackend

**Purpose:** Add a Redis-backed rate-limit counter backend for production / multi-worker correctness.
**Status:** Complete — ready to commit. Production deployment remains disabled.
**Related docs:** [API_CONTRACT](../API_CONTRACT.md) §6 · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md) · [LAUNCH_BLOCKERS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)

---

## 1. Scope

P3-4c follows P3-4b. P3-4b already wired shared app-scoped rate limiting and endpoint-level limits. P3-4c adds the production-shaped Redis backend so future multi-worker deployments do not silently fall back to process-local counters.

No production deploy/cutover was performed.

No real provider, sending, Stripe, SMS, or live scraping was enabled.

---

## 2. Preflight

- `git fetch origin` completed.
- `HEAD` matched `origin/master` at `789c2286e67213bf7e9641d83191a332b164e423` before edits.
- Working tree was clean before edits.
- `.git/*.lock` files: none found.
- No `AutomatedStructure` pytest/Vitest/Next/npm/ruff/black/mypy process was detected as active.

Latest pre-slice commit:

```text
789c228 style(p3-4): format rate limit code
```

---

## 3. Redis backend implementation

Added:

- `backend/app/ratelimit/redis_backend.py`

`RedisRateLimitBackend` implements the existing `RateLimitBackend` Protocol:

```python
async def incr(self, key: str, *, window: timedelta, now: datetime) -> tuple[int, int]
```

Implementation behavior:

- Uses `redis.asyncio` lazily through `RedisRateLimitBackend.from_url()`.
- Uses one atomic Lua script per counter hit:
  - `INCR key`
  - if value is `1`, `EXPIRE key window_seconds`
  - `TTL key`
  - returns `[count, ttl]`
- Keeps fixed-window semantics aligned with the existing in-memory backend.
- Returns `(count, reset_after_seconds)` expected by `RateLimitService`.
- Does not alter key construction. `RateLimitService.build_key()` still owns key shape and still hashes free-text identifiers before storage.

No raw identifiers or secrets are logged or stored by the backend.

---

## 4. Config selection behavior

Added settings:

```text
RATE_LIMIT_BACKEND=in_memory|redis
RATE_LIMIT_REDIS_URL=redis://...
```

Local/test/default behavior:

- `RATE_LIMIT_BACKEND` defaults to `in_memory`.
- `RATE_LIMIT_REDIS_URL` may be unset locally.
- Existing local/mock flows continue using `InMemoryRateLimitBackend` by default.

Redis behavior:

- When `RATE_LIMIT_BACKEND=redis`, app startup builds `RedisRateLimitBackend.from_url(RATE_LIMIT_REDIS_URL)` and stores it in `app.state.rate_limit_backend`.
- `app.state.rate_limit_service` remains the app-scoped `RateLimitService` used by the P3-4b endpoint dependencies.

Dependency added:

- `redis>=5.0` in `backend/pyproject.toml`

The package import is lazy so unit tests can use a fake client and do not require a live Redis server.

`.env.example` was updated with placeholders/non-secret local defaults only.

---

## 5. Production boot/config guard

Updated:

- `backend/app/observability/boot_guard.py`

Production now fails closed unless:

- `rate_limit_backend == "redis"`
- `RATE_LIMIT_REDIS_URL` is a non-placeholder `redis://` or `rediss://` URL

`controlled_demo` does **not** bypass Redis rate-limit backend requirements. This avoids silently weakening production/multi-worker abuse protection.

No Redis reachability/network boot check was added in this slice. The guard is deterministic and configuration-only. Future readiness checks can verify Redis reachability separately without making boot depend on external network timing.

---

## 6. Tests added/updated

Added:

- `backend/tests/test_redis_rate_limit.py`

Updated:

- `backend/tests/test_boot_guard.py`

Coverage added:

- Redis backend increments within the window.
- Redis backend returns correct remaining/reset values through `RateLimitService`.
- Redis backend resets after fixed-window expiry using a fake Redis client.
- Redis receives hashed key output; raw email/identifier is not stored.
- App builder uses `InMemoryRateLimitBackend` by default.
- App builder uses `RedisRateLimitBackend` when configured.
- `create_app()` wires in-memory by default.
- `create_app()` wires Redis when configured.
- Production config fails if Redis backend is missing.
- Production config fails if Redis URL is missing/placeholder/wrong scheme.
- `controlled_demo` does not bypass Redis backend requirement.

No live Redis server is required for tests.

---

## 7. Verification

Backend:

```text
python -m ruff check app tests
PASS

python -m black --check app tests
PASS

python -m mypy app --ignore-missing-imports
PASS

python -m pytest
592 passed, 1 warning
```

Frontend:

```text
npm run lint
PASS

npm run typecheck
PASS

npm run test
122 passed

npm run build
PASS — compiled successfully, generated static pages 27/27
```

Notes:

- Backend warning: existing FastAPI/Starlette `TestClient` deprecation warning.
- Frontend warnings/logs: existing Vite CJS deprecation warning and expected local/mock fallback `NETWORK_ERROR` stderr during tests.

---

## 8. Safety confirmation

Confirmed:

- Production not enabled.
- No deploy performed.
- No real Redis secrets added.
- No `.env` file edited.
- No auth/RBAC/RLS/tenant isolation weakening.
- No billing/send gate bypass.
- No real provider imports added.
- No real sending enabled.
- No Stripe enabled.
- No SMS enabled.
- No live scraping enabled.
- In-memory backend preserved for local/test/default.
- P3-4b endpoint limits preserved.

---

## 9. Remaining blockers / next slice

P3-4c provides Redis backend implementation and config guard only. Remaining future work before actual production cutover:

- Add Redis readiness check if/when production readiness endpoint becomes Redis-aware.
- Provision real Redis/ElastiCache through infrastructure, not in repo secrets.
- Configure production secrets/env through the approved secrets backend.
- Run staging smoke with Redis selected.
- Continue to P3-5/P3-6 only after explicit approval.

---

## Verdict

P3-4c is complete and ready to commit.
