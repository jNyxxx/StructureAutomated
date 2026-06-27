# P3-4a — Rate Limits & Abuse Protection Inspection / Plan

**Purpose:** Evidence for the P3-4a docs-only slice: rate limit infrastructure inspection,
critical bug identification, endpoint gap map, and P3-4b implementation plan.
**Status:** Complete (docs-only — no code changes).
**Related docs:** [API_CONTRACT](../API_CONTRACT.md) · [LAUNCH_BLOCKERS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §6 · [phase-3-3f-clerk-frontend-integration-plan.md](phase-3-3f-clerk-frontend-integration-plan.md)

---

## 1. Git state

- Branch: `master`
- HEAD at slice start: `2c57076` (P3-3f — frontend Clerk integration plan)
- Docs-only slice — no code changes, no backend/frontend gate delta

---

## 2. Existing rate limit infrastructure

The foundation is **already built** (Phase 1 Slice 12). All pieces are production-shaped:

| Component | File | Status |
|---|---|---|
| `RateLimitMiddleware` | `backend/app/middleware/rate_limit.py` | Mounted in `main.py`; DISABLED (`rate_limit_enabled=False`) |
| `RateLimitService` | `backend/app/services/rate_limit.py` | Full key-builder + `check()` + `enforce()` |
| `InMemoryRateLimitBackend` | `backend/app/ratelimit/backend.py` | Fixed-window, `RateLimitBackend` Protocol |
| `RateLimitPolicy` | `backend/app/services/rate_limit.py` | Frozen dataclass: name, limit, window |
| `RateLimitExceeded` | `backend/app/services/rate_limit.py` | `AppError` subclass, HTTP 429, `RATE_LIMITED` |
| `DEFAULT_POLICIES` | `backend/app/services/rate_limit.py` | auth(10/min), webhook(120/min), risky_action(30/min), job(60/min) |
| `JobThrottle` | `backend/app/workers/throttle.py` | Per-tenant, per-job-type worker-side throttle |
| Response headers | `backend/app/middleware/rate_limit.py` | `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`, `Retry-After` |
| Test suite | `backend/tests/test_rate_limit.py` | 9 tests: service, key structure, PII hashing, middleware, JobThrottle |

Key builder supports: `ip`, `tenant_id`, `action`, `job_type`, `identifier` (SHA-256 hashed — PII never in keys).

`RateLimitBackend` is a Protocol → Redis drop-in requires only a matching `incr(key, *, window, now) -> tuple[int, int]` method.

Redis exists in `docker-compose.yml` under `--profile cache` (optional, not core stack).

Global middleware config (`backend/app/config.py`):
- `rate_limit_enabled: bool = False`
- `rate_limit_default_limit: int = 60`
- `rate_limit_window_seconds: int = 60`

---

## 3. Critical bug: per-request backend instantiation

**`sending.py` and `followups.py` both create a new `InMemoryRateLimitBackend()` inside their
service factory dependency on every request:**

```python
# backend/app/routers/sending.py:84  (followups.py:86 is identical)
rate_limiter=RateLimitService(InMemoryRateLimitBackend()),
```

`InMemoryRateLimitBackend` holds counters in an instance-level dict. A new instance per request
= a fresh counter per request = **the `tenant_send` and `tenant_followup` rate limits are
complete no-ops** — every request starts at count 0 and is always allowed, regardless of volume.

This is the highest-priority fix in P3-4b.

**Root cause:** The FastAPI dependency (`_send_gate_service`) is an async generator that yields
a `SendGateService` built with a fresh backend on each invocation. There is no shared state.

**Fix:** Wire a shared `RateLimitService` via `app.state` so the same backend instance (and its
counters) are reused across all requests within a process lifetime.

---

## 4. Existing abuse protections (what works today)

| Protection | Mechanism | Where |
|---|---|---|
| Idempotency (imports) | `Idempotency-Key` header required; DB-backed lock + replay (24h TTL) | `imports.py`, `idempotency_repo.py` |
| Idempotency (campaigns, send-intent, dry-run, followups) | Same | `campaigns.py`, `sending.py`, `followups.py` |
| Tenant isolation | RLS + tenant context per request | All routers |
| Auth guard | `current_principal` dependency | All protected routes |
| Billing gate | `BillingGateService.require_active()` + `require_feature()` | imports, campaigns, sending |
| Send gate | Full check: suppression, compliance, safety, groundedness | `sending.py` |
| Worker job throttle | `JobThrottle` per-tenant per-job-type | `backend/app/workers/throttle.py` |
| Request/correlation IDs | `RequestIdMiddleware` | All requests |
| Structured logging | `RequestLoggingMiddleware` | All requests |

---

## 5. Gap map

### 5.1 Global baseline — disabled

`RateLimitMiddleware` is mounted but `rate_limit_enabled=False`. Requires explicit enable per
environment; local stays disabled (per-endpoint limits are primary); production needs `true`.

### 5.2 Per-endpoint coverage

| Endpoint | Risk | Rate limit today | Gap |
|---|---|---|---|
| `POST /auth/session` | **Critical** — brute-force, credential stuffing | None | Missing per-IP + hashed-email enforce() |
| `GET /auth/me` | Medium — frequent page-load call | None | Per-IP global baseline sufficient |
| `POST /auth/logout`, `POST /auth/logout-all` | Low | None | Acceptable as-is |
| `POST /api/v1/imports/contacts` | **High** — CPU/DB, batch abuse | None (idempotency only) | Missing per-tenant import limit |
| `POST /api/v1/campaigns` | Medium — resource creation | None | Missing per-tenant create limit |
| `POST /api/v1/campaigns/{id}/contacts/select` | High — DB-heavy bulk op | None | Missing per-tenant limit |
| `POST /api/v1/send-gate/dry-run` | High — computation (policy eval) | Wired but **no-op bug** | Fix shared backend |
| `POST /api/v1/send-intents` | **Critical** — send abuse | Wired but **no-op bug** | Fix shared backend |
| `POST /api/v1/followups/*` (run/schedule) | Medium | Wired but **no-op bug** | Fix shared backend |
| `POST /api/v1/review-items` (approve/reject) | Medium — workflow state mutation | None | Per-tenant risky_action sufficient |
| `GET /api/v1/*` (read operations) | Low | None | Global IP baseline sufficient |
| Billing/settings/compliance routes | Low-Medium — admin mutations | None | Per-tenant risky_action policy sufficient |

### 5.3 Multi-worker gap

Single-process `InMemoryRateLimitBackend` does not share state across processes. In production
(multi-worker uvicorn or separate worker process), per-IP limits are not enforced across workers.
**Redis is required for production multi-process correctness** — deferred to P3-4c.

---

## 6. Recommended architecture for P3-4b

### 6.1 Shared backend via `app.state`

```python
# backend/app/main.py (lifespan or app startup)
app.state.rate_limit_backend = InMemoryRateLimitBackend()

# FastAPI dependency (new or inline)
def get_rate_limit_service(request: Request) -> RateLimitService:
    return RateLimitService(request.app.state.rate_limit_backend)
```

Routes receive `RateLimitService` via `Depends(get_rate_limit_service)`. The `app.state` slot
allows a clean Redis swap in P3-4c without touching any route handlers.

### 6.2 Per-endpoint policies to add

| Endpoint | Policy | Scope | Limit | Window |
|---|---|---|---|---|
| `POST /auth/session` | `auth` (existing default) | IP + hashed email | 10 | 1 min |
| `POST /api/v1/imports/contacts` | new `import` | tenant_id | 10 | 5 min |
| `POST /api/v1/campaigns` | `risky_action` (existing) | tenant_id | 30 | 1 min |
| `POST /api/v1/campaigns/{id}/contacts/select` | `risky_action` | tenant_id | 30 | 1 min |
| `POST /api/v1/send-gate/dry-run` | `tenant_send` (fix bug) | tenant_id | 100 | 1 min |
| `POST /api/v1/send-intents` | `tenant_send` (fix bug) | tenant_id | 100 | 1 min |
| `POST /api/v1/followups/*` (run/schedule) | `tenant_followup` (fix bug) | tenant_id | 60 | 1 min |

### 6.3 New policy to add to DEFAULT_POLICIES

```python
"import": RateLimitPolicy("import", limit=10, window=timedelta(minutes=5)),
```

### 6.4 Global middleware enable

`RATE_LIMIT_ENABLED=true` in production env config. For local: keep `False`.

### 6.5 Redis (P3-4c — deferred)

`RateLimitBackend` Protocol makes Redis a drop-in: one new class, swap in `app.state` at startup.
No route changes needed. Redis deferred until P3-4b per-endpoint logic is proven.

---

## 7. Data / storage needs

| Need | Solution | New table? |
|---|---|---|
| Per-IP global baseline | `InMemoryRateLimitBackend` (local) / Redis (prod P3-4c) | No |
| Per-tenant endpoint limits | Same backend, different key scope | No |
| Per-job-type worker throttle | `JobThrottle` already exists | No |
| Persistent usage quotas | `UsageRepository` (read-only aggregation, existing) | No |
| Billing feature gates | `BillingGateService` + `tenant_subscriptions` (existing) | No |

**No new DB tables required.** Rate counters are ephemeral. Idempotency (DB-backed, 24h TTL)
already covers duplicate-send/import prevention independently.

---

## 8. Tests needed in P3-4b

| Test | File | What it proves |
|---|---|---|
| Auth: 11th request in 1 min → 429 | `test_rate_limit_endpoints.py` (new) | Per-IP auth throttle works |
| Auth: different IPs don't share limit | same | IP key scope isolation |
| Import: tenant A 11th import in 5 min → 429 | same | Per-tenant import throttle |
| Import: tenant B unaffected by tenant A counter | same | Tenant key isolation |
| Send-intent: 101st in-window request → 429 | same | tenant_send enforcement after bug fix |
| Send-intent: counter shared across requests | same | Proves no-op bug is fixed |
| Campaign create: 31st request in 1 min → 429 | same | risky_action on campaigns |
| `DEFAULT_POLICIES` includes `"import"` key | `test_rate_limit.py` (update) | Policy registry completeness |
| Shared backend: counter persists across `RateLimitService` instances | `test_rate_limit.py` (update) | Singleton correctness |

---

## 9. P3-4b files (code slice — no Redis)

| File | Change |
|---|---|
| `backend/app/services/rate_limit.py` | Add `"import"` to `DEFAULT_POLICIES` |
| `backend/app/main.py` | Mount shared `InMemoryRateLimitBackend` on `app.state`; add `get_rate_limit_service` dep |
| `backend/app/routers/auth.py` | `enforce()` on `POST /auth/session` (IP + hashed identifier) |
| `backend/app/routers/imports.py` | `enforce()` on `POST /api/v1/imports/contacts` (tenant_id) |
| `backend/app/routers/campaigns.py` | `enforce()` on campaign create + contact-select (tenant_id) |
| `backend/app/routers/sending.py` | Fix no-op bug: use `app.state` backend (not per-request `InMemoryRateLimitBackend()`) |
| `backend/app/routers/followups.py` | Same fix as `sending.py` |
| `backend/tests/test_rate_limit.py` | Add shared-backend singleton + `"import"` policy tests |
| `backend/tests/test_rate_limit_endpoints.py` | New — per-endpoint 429 behavior tests |

`backend/app/config.py`: no change (all needed config fields already exist).

**P3-4c (separate future slice):** `RedisRateLimitBackend` class + `redis[asyncio]` dependency
for production multi-process correctness.

---

## 10. Final verdict

**P3-4a = docs-only.** Infrastructure fully inspected. Critical bug documented and root-caused.
Gap map complete. P3-4b implementation plan is specific and ready to execute.

**P3-4b code is safe to implement immediately.** No blockers, no owner decisions needed.
Priority order:
1. Fix shared backend bug (`sending.py` + `followups.py`) — highest urgency.
2. Add per-endpoint `enforce()` on auth, import, campaign endpoints.
3. Add tests proving fix correctness and per-endpoint 429 behavior.

---

## 11. Honest limits

- No production enable, no real secrets, no `.env` edits, no logic changes.
- No mock auth removed, no local demo broken.
- Backend gates: 576 / frontend: 122 — unchanged (zero code changes this slice).
- The per-request backend bug was introduced before this audit; no code was changed to introduce it.
