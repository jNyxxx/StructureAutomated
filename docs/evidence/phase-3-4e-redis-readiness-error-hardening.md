# P3-4e — Redis Readiness/Error Hardening + Full Green-Pass Closeout

**Purpose:** Close the remaining Redis rate-limit readiness gaps before any next phase.
**Status:** Complete — code + tests + runtime smoke + docs.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `cb15b0a docs(p3-4): add Redis runtime smoke evidence`

---

## 1. Scope

P3-4e fixes the yellow items from P3-4d:

1. Redis-down rate-limit failures previously returned a generic 500.
2. `/ready` did not report Redis readiness when `RATE_LIMIT_BACKEND=redis`.

Stop-gates held:

- Production not enabled.
- No deployment performed.
- No production Redis provisioned or used.
- No real secrets added.
- No real `.env` file edited.
- No providers enabled.
- No real sending enabled.
- No Stripe enabled.
- No SMS enabled.
- No live scraping enabled.
- No P3-5/P3-6 work started.

---

## 2. Preflight

Preflight commands:

```text
git fetch origin
git status --short
git log --oneline -12
git ls-remote origin refs/heads/master
git rev-parse HEAD
git rev-parse origin/master
find .git -name '*.lock' -print
```

Result:

```text
HEAD = cb15b0a4c608759aa400c9fe75b900c30e18bd25
origin/master = cb15b0a4c608759aa400c9fe75b900c30e18bd25
working tree before edits = clean
.git lock files = none found
```

No repo-related concurrent writer/test process was detected.

---

## 3. Implementation summary

### Redis-down error behavior

Updated `RateLimitService.check()` to catch backend counter failures and raise a sanitized application error:

```text
HTTP 503
code = RATE_LIMIT_BACKEND_UNAVAILABLE
message = Rate limit backend unavailable.
details = {}
```

No Redis URL, credentials, raw Redis key, stack trace, token, tenant name, email, or PII is exposed to clients.

Middleware path was also hardened so global/baseline `RateLimitMiddleware` returns the same sanitized 503 envelope instead of allowing middleware-level exceptions to become generic 500s.

`RATE_LIMITED` behavior remains unchanged:

```text
HTTP 429
code = RATE_LIMITED
message = Rate limit exceeded.
```

### Redis readiness

`check_readiness()` now includes rate-limit backend readiness:

- `RATE_LIMIT_BACKEND=in_memory`
  - `rate_limit_backend = in_memory`
  - Redis is not required and is not checked.
- `RATE_LIMIT_BACKEND=redis` and Redis responds to `PING`
  - `rate_limit_backend = redis`
  - `redis = ok`
- `RATE_LIMIT_BACKEND=redis` and Redis is missing/unavailable
  - `rate_limit_backend = redis`
  - `redis = unavailable`
  - readiness returns `ready = false`.

Redis readiness never leaks Redis URL, credentials, or raw driver errors.

Production boot guard from P3-4c is unchanged: production still requires Redis config, and `controlled_demo` does not bypass that requirement.

---

## 4. Tests added/updated

Updated:

- `backend/app/services/rate_limit.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/ratelimit/redis_backend.py`
- `backend/app/database.py`
- `backend/tests/test_rate_limit.py`
- `backend/tests/test_redis_rate_limit.py`
- `backend/tests/test_database.py`

Added/covered tests:

- Redis/backend counter failure raises `503 RATE_LIMIT_BACKEND_UNAVAILABLE`.
- Redis/backend counter failure does not fail open.
- Redis/backend counter failure response does not leak Redis URL, credentials, raw key, email, token, or PII.
- Middleware-level rate-limit backend failure returns sanitized 503.
- Endpoint-level rate-limit backend failure returns sanitized 503 through `/auth/session`.
- Redis working path still returns `429 RATE_LIMITED` at limit.
- `/ready` with `RATE_LIMIT_BACKEND=redis` and Redis available reports `redis=ok`.
- `/ready` with `RATE_LIMIT_BACKEND=redis` and Redis unavailable reports `redis=unavailable` and `ready=false`.
- `/ready` with `RATE_LIMIT_BACKEND=in_memory` does not require Redis.
- Existing P3-4b endpoint limiter tests still pass.
- Existing boot-guard tests still pass.

---

## 5. Runtime smoke

Runtime stack:

```text
docker compose --profile cache up -d db redis
docker compose build backend
docker compose --profile cache run -d \
  --name automatedstructure-backend-redis-smoke \
  -p 8010:8000 \
  -e APP_ENV=local \
  -e RATE_LIMIT_BACKEND=redis \
  -e RATE_LIMIT_REDIS_URL=redis://redis:6379/0 \
  backend
```

Runtime config:

```text
APP_ENV=local
RATE_LIMIT_BACKEND=redis
BACKEND_CLASS=RedisRateLimitBackend
```

Health/liveness:

```text
GET /health -> 200 OK
GET /live -> 200 OK
```

Ready with Redis up:

```json
{
  "status": "not_ready",
  "environment": "local",
  "checks": {
    "database": "ok",
    "migrations": "out_of_date",
    "rate_limit_backend": "redis",
    "redis": "ok"
  }
}
```

Interpretation: Redis readiness is green. Overall local `/ready` stays 503 because the local DB migrations are out of date; this is honest local stack state and not a Redis failure.

Repeated `POST /auth/session` smoke after `redis-cli FLUSHDB`:

```text
auth_1=401
auth_2=401
auth_3=401
auth_4=401
auth_5=401
auth_6=401
auth_7=401
auth_8=401
auth_9=401
auth_10=401
auth_11=429
```

429 body:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded.",
    "details": {"limit": 10, "retry_after": 60},
    "request_id": "req_cd3fe9a13199424492c7488a1939f4fa"
  }
}
```

Redis keys:

```text
rl:auth:ip=172.19.0.1:a=session
```

Redis-down smoke:

```text
docker container stop automatedstructure-redis-1
```

Ready with Redis down:

```json
{
  "status": "not_ready",
  "environment": "local",
  "checks": {
    "database": "ok",
    "migrations": "out_of_date",
    "rate_limit_backend": "redis",
    "redis": "unavailable"
  }
}
```

Rate-limited endpoint with Redis down:

```text
POST /auth/session -> 503
```

503 body:

```json
{
  "error": {
    "code": "RATE_LIMIT_BACKEND_UNAVAILABLE",
    "message": "Rate limit backend unavailable.",
    "details": {},
    "request_id": "req_633f783a47a043f2b1e0a7756c6fdbe5"
  }
}
```

Redis restarted successfully:

```text
docker container start automatedstructure-redis-1
redis-cli PING -> PONG
```

Ready after restart included:

```text
redis = ok
```

---

## 6. Fail-closed and no-leak confirmation

Confirmed:

- Redis unavailable does not fail open.
- Requests do not bypass rate limiting when Redis is unavailable.
- Client receives explicit `503 RATE_LIMIT_BACKEND_UNAVAILABLE`.
- Response body does not expose Redis URL, Redis credentials, raw key, stack trace, token, tenant name, email, or PII.
- `/ready` reports Redis state explicitly when Redis backend is configured.
- In-memory local/test/default behavior remains supported.

---

## 7. Full green-pass gates

Backend:

```text
python -m ruff check app tests
PASS

python -m black --check app tests
PASS

python -m mypy app --ignore-missing-imports
PASS

python -m pytest
598 passed, 1 warning
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

Warnings:

- Backend: existing FastAPI/Starlette `TestClient` deprecation warning.
- Frontend: existing Vite CJS deprecation warning and expected local/mock fallback `NETWORK_ERROR` stderr in tests.

---

## 8. Safety checks

Safety checks performed:

```text
git diff --check
git status --short
changed-file grep for production cutover claims
changed-file grep for real Redis/Clerk/provider secret-looking values
changed-file grep for provider/sending/Stripe/SMS/live-scraping imports
confirm no real .env files changed
```

Expected changed files are limited to Redis readiness/error code, tests, and docs.

No production deployment work was started.

---

## 9. Honest limits

P3-4e proves local runtime Redis readiness and fail-closed Redis outage behavior. It does not provision production Redis/ElastiCache and does not perform a staging/prod deployment.

Remaining future production work:

- Provision real Redis through infrastructure/secrets, not committed files.
- Run staging smoke using deployment-managed Redis config.
- Keep production boot guard active.

---

## Verdict

All green. Safe to proceed to the next planned slice after P3-4 is accepted.
