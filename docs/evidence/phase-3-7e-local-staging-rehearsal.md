# P3-7e-dryrun — Local Staging Rehearsal Using Production Docker Images

**Purpose:** Record the local rehearsal against production Docker images that preceded any real staging deployment.
**Status:** Complete.
**Date:** 2026-06-30 (Asia/Manila)
**Base commit:** `8634f47c1622c504147a74d4102b83cb00b0811e`

---

## 1. Scope and hard stop

P3-7e-dryrun is a local rehearsal only. No staging or production system was modified.

Confirmed not done:

- no AWS provisioning;
- no ECR registry creation or image push;
- no ECS/Fargate service deployment;
- no staging or production release;
- no real `.env` file edit;
- no real secrets added;
- no Resend adapter activation, SDK call, or live email delivery;
- no cold outreach layer enablement;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation change;
- no billing or send-gate bypass.

Code change: `frontend/Dockerfile.prod` already gained `ARG`/`ENV` declarations for `NEXT_PUBLIC_CLERK_MOCK_MODE` and `NEXT_PUBLIC_API_BASE_URL` in commit `8634f47` (pre-existing when this dry-run executed). Default for `NEXT_PUBLIC_CLERK_MOCK_MODE` is `false` (safe — production CI builds get the secure default without passing the flag). The dry-run rehearsal confirmed these additions work correctly. This slice is docs-only — evidence + four doc updates, no new code change.

---

## 2. Environment

| Item | Value |
|---|---|
| Docker Engine client version | 29.5.3 |
| Base commit | `8634f47c1622c504147a74d4102b83cb00b0811e` |
| Backend image tag | `automatedstructure-backend:p3-7e-dryrun-local` |
| Backend image ID | `sha256:aa7caf65c7f1e756041c954991b22a9e4820f110d959d1781db128ede1db2474` |
| Frontend image tag | `automatedstructure-frontend:p3-7e-dryrun-local` |
| Frontend image ID | `sha256:97bf44c2a0dfefb6ad3e9a4aa7fa71b78e18258f266d3eb4ba70725da36181cb` |
| Registry push | None — images are local only |
| `APP_ENV` used | `local` (boot guard is a no-op) |
| Rate limit backend | `in_memory` (no Redis required at `APP_ENV=local`) |
| Auth mode | `MOCK_VERIFIER=true` (default in `config.py`) |
| Database | Compose `db` service — `pgvector/pgvector:pg16` on port 5432 |
| Migration head confirmed | `00022_platform_admin_role` |

---

## 3. Dockerfile.prod fix applied in this slice

**Problem:** `frontend/Dockerfile.prod` runner stage sets `NODE_ENV=production` but previously had no `ARG` declarations for `NEXT_PUBLIC_*` vars. `NEXT_PUBLIC_*` vars are inlined into the Next.js bundle at build time. Without them, `isLocalMockAuthAllowed()` returns `false` in production (`NODE_ENV=production` + no `NEXT_PUBLIC_CLERK_MOCK_MODE=true`) and `ClerkAuthCard` renders `MockAuthProductionBlock` ("Production auth blocked") instead of the login form.

**Fix committed:** already in `8634f47 docs(auth): update AUTH_AND_RBAC §8 to document credential-based demo login replacing removed demo button` before this dry-run slice started.

```dockerfile
# In frontend/Dockerfile.prod builder stage, after COPY . .
ARG NEXT_PUBLIC_CLERK_MOCK_MODE=false
ENV NEXT_PUBLIC_CLERK_MOCK_MODE=$NEXT_PUBLIC_CLERK_MOCK_MODE
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
```

Default `NEXT_PUBLIC_CLERK_MOCK_MODE=false` — production CI builds remain secure without the flag. Local rehearsal overrides with `--build-arg NEXT_PUBLIC_CLERK_MOCK_MODE=true`.

---

## 4. Backend gate results

| Gate | Result |
|---|---|
| `ruff check app tests` | PASS — all checks passed |
| `black --check app tests` | PASS — 214 files unchanged |
| `mypy app --ignore-missing-imports` | PASS — no issues in 156 source files |
| `pytest` | PASS — **731 passed**, 1 warning (StarletteDeprecationWarning), 0 failures, 44.60s |

Note: test count increased from 638 (P3-4g) to 731 — reflects tests added across P3-5/P3-6/P3-7/P3-Demo slices since the last recorded count.

---

## 5. Frontend gate results

| Gate | Result |
|---|---|
| `npm run lint` | PASS — no ESLint warnings or errors |
| `tsc --noEmit` | PASS — 0 errors |
| `vitest --run` | PASS — **141 passed** across 4 test files, 15.11s |
| `npm run build` | PASS — Next.js standalone build, all routes prerendered |

Note: test count increased from 122 (P3-Demo-2) to 141 — reflects tests added in commit `5e04704` (auth credential form + demo button hide).

---

## 6. Image build results

```
# Backend
docker build -f backend/Dockerfile.prod \
  -t automatedstructure-backend:p3-7e-dryrun-local \
  backend/
→ sha256:aa7caf65c7f1e756041c954991b22a9e4820f110d959d1781db128ede1db2474  PASS

# Frontend
docker build -f frontend/Dockerfile.prod \
  --build-arg NEXT_PUBLIC_CLERK_MOCK_MODE=true \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  -t automatedstructure-frontend:p3-7e-dryrun-local \
  frontend/
→ sha256:97bf44c2a0dfefb6ad3e9a4aa7fa71b78e18258f266d3eb4ba70725da36181cb  PASS
```

Both images built from the updated Dockerfiles without error. No registry push.

---

## 7. Database and migration

Compose `db` service (`pgvector/pgvector:pg16`) was already running and healthy before the rehearsal.

Migration one-off container run:

```
docker run --rm \
  --network automatedstructure_default \
  -e APP_ENV=local \
  -e DATABASE_URL="postgresql+asyncpg://app_user:local_dev_password@db:5432/automatedstructure" \
  automatedstructure-backend:p3-7e-dryrun-local \
  alembic upgrade head
```

Output: no migration rows applied — DB was already at head.

Verified with `alembic current`:

```
00022_platform_admin_role (head)
```

Migration head matches code head. ✓

---

## 8. Service startup

Backend started with:

```
docker run -d --name as-backend-dryrun \
  --network automatedstructure_default -p 8000:8000 \
  -e APP_ENV=local \
  -e DATABASE_URL="postgresql+asyncpg://app_user:local_dev_password@db:5432/automatedstructure" \
  -e MOCK_VERIFIER=true \
  -e RATE_LIMIT_BACKEND=in_memory \
  automatedstructure-backend:p3-7e-dryrun-local
```

Frontend started with:

```
docker run -d --name as-frontend-dryrun -p 3000:3000 \
  automatedstructure-frontend:p3-7e-dryrun-local
```

Note: the existing dev compose stack was running prior to the rehearsal. The dev `backend` and `frontend` compose services were stopped to free ports 8000 and 3000, replaced by the prod containers for the duration of the smoke, then restored via `docker compose start backend frontend` after cleanup.

---

## 9. Health / readiness check results

| Endpoint | HTTP status | Key fields |
|---|---|---|
| `GET /health` | 200 | `{"status": "ok"}` |
| `GET /live` | 200 | `{"status": "alive", "service": "backend"}` |
| `GET /ready` | 200 | `{"status": "ok", "environment": "local", "checks": {"database": "ok", "migrations": "up_to_date", "rate_limit_backend": "in_memory"}}` |

All three pass. ✓

---

## 10. Safety smoke results

### Stripe checkout fail-closed

```
POST /api/v1/billing/checkout-session  (no auth)  → 401 UNAUTHENTICATED
POST /api/v1/billing/checkout-session  (mock auth, {}) → 503 STRIPE_CHECKOUT_NOT_AVAILABLE
```

Auth gate fires first. With valid mock auth, Stripe gate fires correctly: `503 STRIPE_CHECKOUT_NOT_AVAILABLE`. ✓

### Stripe portal fail-closed

```
POST /api/v1/billing/portal-session  (no auth)  → 401 UNAUTHENTICATED
POST /api/v1/billing/portal-session  (mock auth, {}) → 503 STRIPE_PORTAL_NOT_AVAILABLE
```

Same pattern — `503 STRIPE_PORTAL_NOT_AVAILABLE`. ✓

### Additional safety confirmations from log review

- `APP_ENV=local` present in every structured log line (`"environment": "local"`) — not `production` or `staging`. ✓
- No Resend SDK/API call visible in logs. ✓
- No Stripe API call visible in logs. ✓
- `LIVE_EMAIL_SENDING_ENABLED=false` (config.py default). ✓
- No registry push. ✓
- No deployment. ✓

---

## 11. Log review results

Backend (`docker logs as-backend-dryrun`):

- Boot: `Application startup complete.` — no boot guard failures (expected at `APP_ENV=local`).
- All requests logged as `environment: "local"`.
- No DSN, Redis URL, JWT secret, Resend API key, Stripe secret, or any credential value visible.
- No 5xx errors on health endpoints.
- Stripe gate errors logged as `WARNING app.error` with only the error code — no credential leakage.

Frontend (`docker logs as-frontend-dryrun`):

- `▲ Next.js 14.2.35 — Ready in 92ms` — clean startup.
- No errors.

Secret-leakage grep (`grep -iE "(password|sk_|pk_live|jwt_secret|resend_|stripe_secret|dsn:|postgresql://|postgresql\+asyncpg://)"` on backend logs): **zero matches**. ✓

---

## 12. Browser smoke result

Note: commit `5e04704` removed the separate "Continue with Demo Account" button and replaced it with a credential form. Mock login credentials: `test@example.com` / `password`.

The following were verified manually in browser:

| Check | Result |
|---|---|
| `http://localhost:3000/login` loads | PASS |
| Email + password form visible (not `MockAuthProductionBlock` error) | PASS — confirms `NEXT_PUBLIC_CLERK_MOCK_MODE=true` was baked correctly |
| Enter `test@example.com` / `password` → Sign in | PASS |
| Redirect to `/dashboard` | PASS |
| Dashboard loads as `owner@example.com` | PASS |
| Refresh — session persists (`as_mock_session` in localStorage) | PASS |
| Sign out — returns to signed-out state | PASS |

---

## 13. Mock product smoke result

The following frontend pages were verified to load without JS errors or 5xx responses after logging in as the mock demo user:

| Page/flow | Result |
|---|---|
| `/contacts` — contacts/prospects list | PASS |
| `/campaigns` — campaign list | PASS |
| Campaign create flow | PASS — no 500 |
| Draft/evidence view | PASS |
| Review queue | PASS — pending item visible |
| Send-gate dry-run | PASS — blocked result returned, no real send |
| Mock send intent | PASS — outbound record appears |
| Audit trail | PASS |
| Billing/access | PASS — mock billing state |
| Deliverability/outcomes | PASS |

---

## 14. Cleanup

```
docker stop as-backend-dryrun as-frontend-dryrun
docker rm as-backend-dryrun as-frontend-dryrun
docker compose start backend frontend   # restore dev stack
```

Images retained locally as evidence (`p3-7e-dryrun-local` tags). Not pushed.

---

## 15. Honest limits

This rehearsal does **not** prove staging or production readiness. The following were **not** tested:

| Limit | Impact |
|---|---|
| `APP_ENV=local` used — boot guard is a no-op | Boot guard conditions (secrets, Clerk, Redis, RLS role) were not exercised. A real staging deploy must use `APP_ENV=staging` or `APP_ENV=production`. |
| No managed Redis — `in_memory` rate limit | Redis rate-limit backend was not exercised. Real staging uses `RATE_LIMIT_BACKEND=redis`. |
| No real Clerk auth — mock verifier + token-sentinel | Real JWKS/RS256 token validation not tested here. |
| No AWS Secrets Manager / KMS | Secret resolution from managed secret store not tested. |
| No RDS — local Postgres via compose | Production DB role, least-privilege, and RLS-at-DB-level under the real app role not tested here. |
| No real domain / TLS | HTTPS, CORS, HSTS not tested. |
| No registry push | Images are local; no ECR/registry path tested. |
| Browser smoke was manual | No automated e2e harness. |
| No Redis-down sanitized 503 smoke | Redis not running; in_memory backend used. |

Production staging deploy remains blocked on all §2 prerequisites in [phase-3-7e-staging-release-runbook-plan.md](phase-3-7e-staging-release-runbook-plan.md).

---

## 16. Files created / updated

Created:

- `docs/evidence/phase-3-7e-local-staging-rehearsal.md`

Note: `frontend/Dockerfile.prod` ARG/ENV fix was pre-existing (committed in `8634f47` before this slice executed). This slice is docs-only.

Updated:

- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 17. Final verdict

P3-7e-dryrun is complete. Production Docker images build, boot, migrate, and serve health endpoints cleanly. Mock login via credential form (`test@example.com` / `password`) works in the prod frontend container when `NEXT_PUBLIC_CLERK_MOCK_MODE=true` is baked at build time. Stripe gates are fail-closed. No secrets leaked. No real provider calls. No deployment.

Actual staging deploy remains blocked on §2 open prerequisites.
