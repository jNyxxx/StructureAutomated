# P3-7e-plan — Staging Release Runbook and Go/No-Go Checklist

**Purpose:** Define the staging release runbook, go/no-go checklist, hard stop conditions, rollback plan, and required evidence bundle before any actual staging deployment.
**Status:** Docs-only plan complete.
**Date:** 2026-06-30 (Asia/Manila)
**Base commit:** `5e04704 feat(auth): require test@example.com / password credentials and visually hide demo button`

---

## 1. Scope and hard stop

P3-7e-plan is documentation only.

Confirmed not done:

- no AWS provisioning;
- no ECR registry creation or image push;
- no ECS/Fargate service deployment;
- no staging or production release;
- no real `.env` file edit;
- no application, config, migration, Dockerfile, workflow, or package change;
- no real secrets added;
- no Resend adapter, SDK, API call, or live email delivery;
- no cold outreach layer enablement;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation change;
- no billing or send-gate bypass.

---

## 2. Staging release prerequisites

All values below are **open** — no staging deploy can proceed until each is supplied and each approver is named.

| Value | Status |
|---|---|
| AWS account ID | Open |
| AWS region | Open |
| Deployment platform (ECS/Fargate or approved alt) | Open |
| ECR registry target | Open |
| Staging frontend domain (e.g. `staging.automatedstructure.com`) | Open |
| Staging API domain (e.g. `api-staging.automatedstructure.com`) | Open |
| DNS/TLS owner | Open |
| Secrets Manager owner | Open |
| KMS key alias / ID | Open |
| RDS instance class, storage, backup retention | Open |
| Redis/ElastiCache target and sizing | Open |
| Backup retention / RPO / RTO | Open |
| Alert recipients (CloudWatch / Slack / email) | Open |
| Incident commander / escalation owner | Open |
| Clerk staging values (`AUTH_PROVIDER_ISSUER`, JWKS URL, publishable key, secret key ref) | Open |
| Staging migration approver | Open |
| Staging rollback approver | Open |
| Staging deployment approver | Open |
| Confirmation Resend stays disabled in staging until P3-5f+ gates clear | Open |
| Worker command decision (disable worker or use approved command) | Open |

---

## 3. Image / build procedure

This procedure describes what must happen before and during any approved staging deploy. No registry push is performed in P3-7e-plan.

### 3.1 Pre-build gate confirmation

Before building images for a staging candidate:

```
cd backend
python -m ruff check app tests
python -m black --check app tests
python -m mypy app --ignore-missing-imports
python -m pytest
alembic upgrade head / downgrade base / upgrade head (migration smoke)

cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

All must pass. CI `docker-build-validation` job must also be green (builds both images locally in CI).

### 3.2 Backend production image build

```
docker build -f backend/Dockerfile.prod \
  -t <registry>/automatedstructure-backend:<git_sha> \
  -t <registry>/automatedstructure-backend:staging-candidate-<short_sha> \
  backend
```

Record the image digest:

```
docker inspect <registry>/automatedstructure-backend:<git_sha> \
  --format '{{.Id}}'
```

### 3.3 Frontend production image build

```
docker build -f frontend/Dockerfile.prod \
  -t <registry>/automatedstructure-frontend:<git_sha> \
  -t <registry>/automatedstructure-frontend:staging-candidate-<short_sha> \
  frontend
```

Record the image digest:

```
docker inspect <registry>/automatedstructure-frontend:<git_sha> \
  --format '{{.Id}}'
```

### 3.4 Tagging rules

Required tags:

```
<git_sha>
staging-candidate-<short_sha>
```

Prohibited: `latest` as the sole deploy tag.

### 3.5 Registry push gate

Do not push images to any registry until:

- ECR target confirmed and credentials supplied;
- Deployment approver has signed off;
- All §2 open values are filled.

---

## 4. Migration procedure

Before backend service starts in staging:

1. Build the backend production image (reused for migration one-off task).
2. Start a one-off migration ECS task using the backend image with staging DB secret refs injected through Secrets Manager/KMS.
3. Migration command:
   ```
   alembic upgrade head
   ```
4. Confirm Alembic head matches code head after migration completes.
   Expected current head: `00022_platform_admin_role`.
5. Migration approver must sign off before backend service starts traffic.
6. Record migration output without secrets (no DSN in logs or evidence).
7. If migration fails: **stop**. Do not start the backend service.
   - Investigate: forward-fix vs rollback decision.
   - Forward-fix: preferred if migration is non-destructive.
   - Rollback: `alembic downgrade -1` if safe and rollback-approver signs off; for destructive migrations, restore from pre-migration snapshot.
8. Never run migrations from a developer machine against staging except under a documented emergency process.

---

## 5. Service startup procedure

After migration approver signs off:

### 5.1 Backend service

1. Start backend ECS service (or approved equivalent) using the backend image.
2. Inject staging secret refs through Secrets Manager/KMS path — no raw values in task definition.
3. Required environment:
   - `APP_ENV=staging` (not `production`)
   - `RATE_LIMIT_BACKEND=redis`
   - `RATE_LIMIT_REDIS_URL` from secret ref
   - `AUTH_PROVIDER_ISSUER` from secret ref (or approved mock-auth demo mode if Clerk not yet available)
   - All other refs per `docs/STAGING_ENVIRONMENT_TEMPLATE.md`
4. Boot guard must pass at startup — any config failure aborts.
5. Confirm runtime DB role: `NOSUPERUSER`, `NOBYPASSRLS`.

### 5.2 Frontend service

1. Start frontend ECS service using the frontend image.
2. `NEXT_PUBLIC_API_BASE_URL` = staging API domain (no trailing slash).
3. Clerk staging publishable key from approved config path (or approved mock mode).

### 5.3 Worker service

**Disabled by default.** Do not start the worker unless a specific approved entrypoint command is recorded and the deployment approver confirms worker readiness.

### 5.4 Redis

Redis/ElastiCache must be reachable before backend accepts traffic. Confirm via `/ready` response.

### 5.5 Readiness verification

After services start, verify:

- `GET /health` → `200`
- `GET /live` → `200`
- `GET /ready` → `{"database": "ok", "migrations": "up_to_date", "redis": "ok", "rate_limit_backend": "redis"}`

If `/ready` is not fully `ok`, do not proceed to smoke checklist.

---

## 6. Staging smoke checklist

Run after all services pass `/ready`. All 21 items must pass before staging is accepted.

| # | Check | Pass criteria |
|---|---|---|
| 1 | `GET /health` | 200 |
| 2 | `GET /live` | 200 |
| 3 | `GET /ready` | `database: ok`, `migrations: up_to_date`, `redis: ok` |
| 4 | Frontend loads | Page renders without JS errors; no CSP / CORS violation |
| 5 | Frontend reaches backend | Frontend API call returns expected JSON shape |
| 6 | Auth smoke | Clerk staging login works (or approved mock-auth staging demo mode) |
| 7 | Tenant/RLS smoke | Tenant A query under tenant B context returns empty result |
| 8 | Mock billing gate | `GET /api/v1/billing/access` returns expected mock billing state |
| 9 | Campaign/contact flow | Create contact → create campaign → no server error |
| 10 | Draft/evidence flow | Mock draft generation produces evidence record |
| 11 | Review queue | Human review queue shows pending item |
| 12 | Send-gate dry-run | Send-gate evaluates intent and blocks — does NOT produce a real send |
| 13 | Mock send intent confirmed | No real email delivered; confirm `EMAIL_PROVIDER=mock` in running config |
| 14 | Cold outreach blocked | `send_layer` guard returns `COLD_OUTREACH_NOT_ALLOWED` for cold_outreach intent |
| 15 | Resend transactional disabled | `LIVE_EMAIL_SENDING_ENABLED=false` confirmed; no live Resend adapter call |
| 16 | Stripe checkout disabled | `POST /api/v1/billing/checkout-session` returns fail-closed `STRIPE_CHECKOUT_DISABLED` |
| 17 | Stripe portal disabled | `POST /api/v1/billing/portal-session` returns fail-closed `STRIPE_BILLING_PORTAL_DISABLED` |
| 18 | Rate limit smoke | Repeated `POST /auth/session` returns 429 after policy threshold |
| 19 | Redis-down smoke | Controlled Redis outage returns sanitized `503 RATE_LIMIT_BACKEND_UNAVAILABLE`, no URL leakage |
| 20 | Audit event smoke | Action (e.g. campaign create) produces audit event record |
| 21 | Log review | Logs contain no DSN, Redis URL, JWT secret, Clerk secret, or provider key |

---

## 7. Hard stop conditions

Stop the staging release immediately if any are true:

1. Real `.env` secrets committed to the repo.
2. Placeholder secrets detected in running service (`CHANGE_ME`, empty `JWT_SECRET`, etc.).
3. Docker image build failure.
4. Migration fails or Alembic head is mismatched from code head.
5. `/ready` not fully `ok` for `database`, `migrations`, or `redis`.
6. Redis unavailable when `RATE_LIMIT_BACKEND=redis` is configured.
7. Runtime DB role has `SUPERUSER` or `BYPASSRLS`.
8. Boot guard logs any config failure at startup.
9. Clerk/auth unavailable and no approved mock-auth staging demo mode is recorded.
10. Any live send enabled (`LIVE_EMAIL_SENDING_ENABLED=true` or a real Resend API call occurs).
11. Cold outreach intent routes to Resend instead of being blocked by `send_layer`.
12. Stripe money movement enabled.
13. SMS enabled.
14. Live scraping enabled.
15. No rollback approver identified before deploy.
16. No alert recipient identified before deploy.
17. Migration approver did not sign off before backend service starts.
18. Deployment approver did not sign off.

---

## 8. Rollback plan

If staging deploy fails or any smoke item does not pass:

1. Identify previous backend and frontend image tags and digests (must be recorded in evidence before the deploy begins).
2. Roll back ECS service or task definition to the previous task definition revision.
3. DB rollback stance:
   - Do not auto-roll back DB unless migration was destructive AND a backup snapshot exists AND rollback is safer than a forward-fix.
   - Default: forward-fix.
4. Migration rollback rules:
   - Non-destructive migration: `alembic downgrade -1` if rollback-approver signs off.
   - Destructive migration: restore from pre-migration snapshot with rollback-approver sign-off.
5. Disable live flags:
   - `LIVE_EMAIL_SENDING_ENABLED=false`
   - `LIVE_COLD_SENDING_ENABLED=false` (once the cold-outreach layer exists)
   - Any other kill switches active at deploy time.
6. Stop worker service if it was running.
7. Verify `/ready` returns `ok` after rollback completes.
8. Write an incident/evidence note recording:
   - What failed.
   - Rollback action taken.
   - Image tag/task definition reverted to.
   - Approver names.
   - Timestamps.

---

## 9. Evidence bundle required for real staging deploy

The actual P3-7e staging deploy (when approved and performed) must produce the following evidence bundle:

| Evidence item | Required |
|---|---|
| Source commit SHA | Yes |
| Backend image tag + digest | Yes |
| Frontend image tag + digest | Yes |
| Worker image/command if active | If worker enabled |
| Migration one-off task output (no secrets) | Yes |
| Alembic current head confirmation (`00022_platform_admin_role`) | Yes |
| `GET /health` response | Yes |
| `GET /live` response | Yes |
| `GET /ready` response (database/migrations/redis all ok) | Yes |
| Frontend-to-backend call proof | Yes |
| Tenant/RLS smoke result | Yes |
| Rate-limit Redis 429 proof | Yes |
| Redis-down sanitized 503 proof | Yes |
| Mock billing gate proof | Yes |
| Send-gate dry-run only proof | Yes |
| Confirmation no real send occurred | Yes |
| Cold-outreach `COLD_OUTREACH_NOT_ALLOWED` proof | Yes |
| Stripe checkout/portal fail-closed proof | Yes |
| Audit event smoke proof | Yes |
| Log review result (no secret leakage) | Yes |
| Rollback target recorded (image tag + task definition) | Yes |
| Migration approver name + timestamp | Yes |
| Deployment approver name + timestamp | Yes |
| Rollback approver name + timestamp | Yes |
| Alert recipient confirmed | Yes |
| Emergency-stop owner confirmed | Yes |

---

## 10. Remaining open prerequisites

All §2 values remain open. Staging deploy is blocked until every row in §2 is filled and every approver is named.

---

## 11. Files created / updated

Created:

- `docs/evidence/phase-3-7e-staging-release-runbook-plan.md`

Updated:

- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

No application, config, migration, Dockerfile, workflow, package, or real environment file changed.

---

## 12. Final verdict

P3-7e-plan is complete as a docs-only staging release runbook and go/no-go checklist.

No deployment performed. No infrastructure provisioned. No secrets added. No registry push.

Actual staging deploy remains blocked until §2 owner/operator values are supplied and a later slice explicitly approves deployment.
