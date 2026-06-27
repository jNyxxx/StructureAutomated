# P3-4d — Redis Runtime Smoke + Rate-Limit Ops Evidence

**Purpose:** Prove the Redis-backed rate-limit backend works against a real local Redis container/service in a running local/staging-like stack.
**Status:** Complete — docs-only runtime evidence slice.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `600f2c7 feat(p3-4): add Redis rate limit backend`

---

## 1. Scope

P3-4d verifies the P3-4c Redis backend at runtime. It does not change application code.

Confirmed stop-gates:

- Production not enabled.
- No deployment performed.
- No production Redis used.
- No real Redis secrets added.
- No real `.env` file edited.
- No providers enabled.
- No real sending enabled.
- No Stripe enabled.
- No SMS enabled.
- No live scraping enabled.
- No P3-5/P3-6 started.

---

## 2. Preflight

Commands run:

```text
git fetch origin
git status --short
git log --oneline -12
git ls-remote origin refs/heads/master
git rev-parse HEAD
git rev-parse origin/master
find .git -name '*.lock' -print
docker version
docker compose version
```

Result:

```text
HEAD = 600f2c7e3febd87df414c5d7d46416fb92f0a961
origin/master = 600f2c7e3febd87df414c5d7d46416fb92f0a961
working tree before docs = clean
.git lock files = none found
Docker Desktop was initially not running, then started from the local DockerDesktop install.
Docker client/server became available.
Docker Compose version = v5.1.4
```

No repo-related concurrent pytest/Vitest/Next/npm/ruff/black/mypy process was detected.

---

## 3. Local runtime used

Compose services used:

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

Runtime status during smoke:

```text
automatedstructure-db-1      Up (healthy)   0.0.0.0:5432->5432/tcp
automatedstructure-redis-1   Up             0.0.0.0:6379->6379/tcp
automatedstructure-backend-redis-smoke Up   0.0.0.0:8010->8000/tcp
```

Backend logs showed:

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

---

## 4. Runtime config used

Backend smoke container config:

```text
APP_ENV=local
RATE_LIMIT_BACKEND=redis
RATE_LIMIT_REDIS_URL=redis://redis:6379/0
```

Redis backend selection was confirmed inside the running backend container:

```text
APP_ENV=local
RATE_LIMIT_BACKEND=redis
RATE_LIMIT_REDIS_URL=redis://redis:6379/0
BACKEND_CLASS=RedisRateLimitBackend
IS_REDIS=True
```

This proves the runtime backend was Redis, not `InMemoryRateLimitBackend`.

---

## 5. Health / live / ready results

`GET /health`:

```text
HTTP/1.1 200 OK
{"status":"ok"}
```

`GET /live`:

```text
HTTP/1.1 200 OK
{"status":"alive","service":"backend"}
```

`GET /ready`:

```text
HTTP/1.1 503 Service Unavailable
{"status":"not_ready","environment":"local","checks":{"database":"ok","migrations":"out_of_date"}}
```

Interpretation:

- Backend booted successfully with Redis selected.
- Liveness passed.
- Readiness correctly reported local DB/migration state as not ready because migrations were out of date in this local runtime.
- This was not a Redis failure.

---

## 6. HTTP Redis counter / 429 result

Redis DB was flushed before smoke to isolate keys:

```text
redis-cli FLUSHDB
```

`POST /auth/session` was hit 11 times using the same IP/identifier path. The first 10 requests returned `401` because an intentionally invalid local smoke token was used, but each request still passed through the rate-limit dependency and incremented Redis. The 11th request returned `429` before auth result mattered.

Observed:

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
{"error":{"code":"RATE_LIMITED","message":"Rate limit exceeded.","details":{"limit":10,"retry_after":59},"request_id":"req_13c41be30de14653befcf30a9f272650"}}
```

429 headers included the standard request/correlation IDs. Endpoint-level dependency errors did not emit `Retry-After` / `RateLimit-*` headers in this path; retry data is present in the standard error envelope details.

Redis keys created:

```text
rl:auth:ip=172.19.0.1:a=session
rl:auth:ip=172.19.0.1:a=session_identifier:id=1ea966a3461ce8d0
```

This proves the counter is shared across requests and does not reset per request.

---

## 7. Tenant isolation result

Redis DB was flushed before tenant isolation smoke.

`POST /api/v1/imports/contacts` was hit 11 times for tenant A and once for tenant B.

Tenant A:

```text
tenant_a_import_1=403
tenant_a_import_2=403
tenant_a_import_3=403
tenant_a_import_4=403
tenant_a_import_5=403
tenant_a_import_6=403
tenant_a_import_7=403
tenant_a_import_8=403
tenant_a_import_9=403
tenant_a_import_10=403
tenant_a_import_11=429
```

Tenant A first 10 requests reached downstream billing/permission logic and returned `403`; they were still counted by Redis. The 11th request was blocked at rate-limit layer:

```json
{"error":{"code":"RATE_LIMITED","message":"Rate limit exceeded.","details":{"limit":10,"retry_after":299},"request_id":"req_f0177c9a536c49a5a75864bf5d472a5c"}}
```

Tenant B first request after tenant A hit the limit:

```text
tenant_b_import_1=500
```

Tenant B did **not** receive `429`. It hit a downstream local-stack/internal error instead, proving tenant B was not blocked by tenant A's Redis counter.

Redis tenant-scoped keys:

```text
rl:import:t=11111111-1111-1111-1111-111111111111:a=contacts_import
rl:import:t=22222222-2222-2222-2222-222222222222:a=contacts_import
```

This proves tenant-scoped Redis counters are isolated by tenant ID.

---

## 8. Reset behavior result

A short-window direct runtime smoke was run inside the backend smoke container using the real Redis service and `RateLimitService`:

```text
policy = RateLimitPolicy('smoke_reset', limit=1, window=2 seconds)
```

Result:

```text
reset_first_allowed=True
reset_second_allowed=False
reset_after_sleep_allowed=True
reset_after_sleep_remaining=0
```

This proves Redis TTL expiry resets the fixed-window counter.

---

## 9. Redis key PII safety result

Redis key grep checked for raw email/token/secret-like values:

```text
jane@example.com
owner@example.com
token-sentinel
fake-valid-token
smoke-token
Bearer
CHANGE_ME
sk_live
pk_live
```

Result:

```text
(no matches)
```

Observed keys used structural dimensions and hashed identifiers only. No raw email, raw bearer token, raw tenant name, or secret-looking value appeared in Redis keys.

Note: tenant-scoped route keys include tenant UUIDs by design. They do not include tenant names or contact/customer PII.

---

## 10. Redis failure behavior

Redis container was stopped locally:

```text
docker container stop automatedstructure-redis-1
```

A rate-limited endpoint was then called while backend remained up:

```text
POST /auth/session
HTTP/1.1 500 Internal Server Error
{"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred.","details":{},"request_id":"req_7530e24fb9bb4b5d88d3ffff64a0e580"}}
```

Interpretation:

- Current runtime behavior does not fail open when Redis is unavailable.
- The request does not bypass rate limiting.
- It fails as a standard `INTERNAL_ERROR` envelope.
- Future improvement: map Redis backend availability failures to a more explicit `RATE_LIMIT_BACKEND_UNAVAILABLE` / 503-style error and add Redis readiness to `/ready` before production cutover.

Redis was restarted after this smoke:

```text
redis-cli PING -> PONG
```

---

## 11. Boot guard / config behavior

P3-4c boot guard behavior remains intact:

- Production requires `RATE_LIMIT_BACKEND=redis`.
- Production requires a non-placeholder `redis://` or `rediss://` `RATE_LIMIT_REDIS_URL`.
- `controlled_demo` does not bypass Redis requirement.
- P3-4d did not weaken the boot guard.

P3-4d did not run the app in production mode.

---

## 12. Gate results

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

Warnings:

- Backend: existing FastAPI/Starlette `TestClient` deprecation warning.
- Frontend: existing Vite CJS deprecation warning and expected local/mock fallback `NETWORK_ERROR` stderr in tests.

---

## 13. Safety checks

Safety checks performed:

```text
git diff --check
changed-file grep for production cutover claims
changed-file grep for secret-looking Redis/Clerk/provider values
grep app changes for provider/sending/Stripe/SMS/live-scraping imports
```

Results:

- `git diff --check`: PASS.
- No production cutover was made.
- No real Redis/Clerk/provider secrets were added.
- No provider/sending/Stripe/SMS/live-scraping imports were added.
- Only docs were changed in this slice.

---

## 14. Honest limits / next work

P3-4d proves local runtime Redis rate limiting works with a real Redis container. It does not prove cloud/staging Redis provisioning.

Remaining before production cutover:

- Add Redis readiness to `/ready` or deployment smoke checks.
- Provision real Redis/ElastiCache through infrastructure, not committed env files.
- Run staging smoke using deployment-managed secrets/config.
- Improve Redis-unavailable error mapping from generic 500 to explicit rate-limit backend unavailable response.

---

## Verdict

P3-4d complete.
