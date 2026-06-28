# P3-7a — Deployment / Ops Readiness Inspection + Staging Plan

**Purpose:** Inspect deployment and operations readiness and define the staging plan before any infrastructure work.
**Status:** Docs-only readiness plan.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `e7459af docs(p3-5): record owner approval and Resend roadmap`

---

## 1. Scope and hard stop

P3-7a is an inspection and staging-plan slice only.

No runtime or infrastructure action was performed:

- no AWS provisioning;
- no production cutover;
- no real `.env` file edit;
- no secrets added;
- no Resend adapter, SDK, or API call;
- no live email delivery;
- no Stripe, SMS, or live scraping;
- no boot-guard weakening;
- no auth/RBAC/RLS/tenant-isolation changes;
- no billing/send-gate bypass;
- no database migration or application code change.

---

## 2. Inspection inputs

Inspected:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `.env.example` key inventory only
- `backend/app/config.py`
- `backend/app/observability/boot_guard.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/workers/worker.py`
- `backend/app/services/queue.py`
- `backend/alembic.ini`
- `backend/migrations/versions/*`
- `frontend/package.json`
- `frontend/next.config.mjs`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/ARCHITECTURE.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`
- `docs/evidence/phase-3-4f-rate-limit-abuse-protection-acceptance.md`
- `docs/evidence/phase-3-5e-owner-approval-resend-roadmap.md`

---

## 3. Current deployment state

### 3.1 Local-only pieces

Current runtime shape is local/mock-first:

- `docker-compose.yml` is explicitly labeled local development stack.
- Compose includes Postgres/pgvector, backend, worker, frontend, n8n, optional LocalStack, and optional Redis.
- `.env.example` is placeholder-only and intended for local copy to `.env`.
- P3-5e records Resend as provider direction, but safe runtime defaults still keep `EMAIL_PROVIDER=mock` and `LIVE_EMAIL_SENDING_ENABLED=false`.

### 3.2 Docker readiness

Current Docker files are development-oriented:

- `backend/Dockerfile` uses `python:3.12-slim`, editable install, and `uvicorn --reload`.
- `frontend/Dockerfile` uses `node:20-alpine`, `npm install`, and `npm run dev`.
- `docker-compose.yml` mounts source directories into containers and uses dev ports.
- These are useful for local development, not final production runtime images.

Production gaps:

- no production multi-stage backend image;
- no production Next.js runtime image;
- no non-root runtime user documented in Dockerfiles;
- no image healthcheck in Dockerfiles;
- no production worker command wired in Compose;
- no image version/tag/rollback convention yet.

### 3.3 Backend readiness

Backend readiness is strong at application level:

- `create_app()` wires middleware, routers, rate limiter, request IDs, logging, auth service, and health routes.
- Lifespan runs `enforce_config(settings)`.
- In production with DB configured, lifespan also runs boot-guard database checks.
- `/ready` checks DB connectivity, Alembic head, and Redis readiness when Redis backend is selected.

Backend production gaps:

- production config values are not supplied;
- real Clerk production values still need cutover smoke;
- production Docker image hardening is missing;
- staging synthetic smoke path is not yet recorded as evidence.

### 3.4 Frontend readiness

Frontend readiness is good for build/test, not yet final hosting:

- `package.json` has `dev`, `build`, `start`, `lint`, `typecheck`, and `test` scripts.
- `next.config.mjs` is minimal with `reactStrictMode=true`.
- CI runs lint/typecheck/test/build.

Frontend production gaps:

- production hosting target is not selected;
- production image/build strategy is not hardened;
- public runtime env matrix is not recorded;
- real Clerk frontend integration remains separately gated;
- staging domain/TLS not selected.

### 3.5 Worker readiness

Worker foundation exists but runtime packaging is not staging-ready:

- `WorkerLoop` exists and is stoppable/testable.
- `QueueService` claims jobs through worker context and runs handlers under tenant context.
- Queue/outbox uses Postgres as source of truth; production SQS dispatch remains architecture-level.
- Compose worker command still prints a placeholder and sleeps.

Worker production gaps:

- real worker entrypoint/command must be defined;
- process supervision and graceful shutdown must be specified;
- per-job handlers and worker concurrency model must be finalized;
- DLQ/alert routing must be operationalized;
- worker boot guard parity must be proven in staging.

### 3.6 DB / migration readiness

DB/migration readiness is strong locally and in CI:

- Alembic config exists.
- Migration versions are present through `00022_platform_admin_role.py`.
- CI runs Alembic upgrade/downgrade/upgrade against Postgres + pgvector.
- P3-2 live DB smoke proved local migration head, RLS-forced tables, tenant isolation, and protected API smoke.
- Boot guard checks migration head and RLS state in production.

Production gaps:

- RDS target/config not selected;
- least-privilege runtime DB role must be provisioned;
- backup retention/RPO/RTO not selected;
- restore drill not performed for staging/prod target;
- migration one-off task process not documented with operator approvals.

### 3.7 Redis readiness

Redis app track is green; infrastructure is not provisioned:

- P3-4f accepted Redis/rate-limit track as green.
- Redis backend is config-driven via `RATE_LIMIT_BACKEND=redis` and `RATE_LIMIT_REDIS_URL`.
- Production boot guard requires Redis backend and non-placeholder Redis URL.
- `/ready` reports Redis state when Redis backend is configured.
- Redis-down behavior fails closed with `503 RATE_LIMIT_BACKEND_UNAVAILABLE`.

Production gaps:

- ElastiCache/Redis target not selected;
- Redis URL/secret path not supplied;
- staging smoke against managed Redis not performed;
- Redis outage alert not wired.

### 3.8 Secrets readiness

Design is clear but implementation is not complete:

- Production secrets are expected through AWS Secrets Manager + KMS.
- Boot guard requires `secret_backend='aws'` in production.
- No raw provider secrets should enter DB/logs/audit/frontend/prompts/client responses.
- `.env.example` contains placeholders only.

Production gaps:

- Secrets Manager naming convention not finalized;
- KMS key ID not supplied;
- IAM task role permissions not designed in deploy artifacts;
- secret rotation procedure not tested;
- Resend secret refs are still missing per P3-5e.

### 3.9 Observability readiness

Observability is partly designed:

- structured log shape is documented;
- request/correlation ID middleware exists;
- `/health`, `/live`, and `/ready` exist;
- runbook defines alerts and response steps;
- in-product observability and LangSmith faithfulness logging are required.

Production gaps:

- CloudWatch/log aggregation target not wired;
- metrics dashboard not created;
- alert recipients not selected;
- incident runbooks not tested;
- staging evidence bundle not created.

---

## 4. Production blockers

Production remains blocked by these deployment/ops items:

1. Production-grade backend Dockerfile.
2. Production-grade frontend Dockerfile / hosting strategy.
3. Worker runtime command/image/service definition.
4. AWS account, region, and platform target decision.
5. AWS Secrets Manager + KMS wiring.
6. RDS PostgreSQL config and least-privilege app role.
7. Redis/ElastiCache config for rate limiting.
8. Domain/TLS plan for app and API.
9. CI/CD promotion gates and approval policy.
10. Backup/restore drill, RPO, and RTO.
11. Monitoring/logging/alerts and alert recipients.
12. Rollback plan with previous image/task definition retention.
13. Migration plan using one-off migration task.
14. Staging smoke plan and evidence bundle.
15. Clerk production/dev values and frontend integration cutover.
16. Resend concrete pre-smoke values from P3-5e before live-send work.
17. Counsel-approved legal copy before any external live email.
18. Stripe/SMS/live scraping remain deferred and must not be included in P3-7.

---

## 5. Staging architecture proposal

Recommended staging target if AWS remains the deployment platform:

| Component | Proposed staging shape | Notes |
|---|---|---|
| Backend service | ECS/Fargate service behind ALB | Runs FastAPI app with production-like settings, but no live sending/Stripe/SMS. |
| Frontend service | ECS/Fargate Next runtime or approved managed frontend host | Must use staging API URL and staging Clerk/public config. |
| Worker service | ECS/Fargate worker service | Uses same backend image with worker command once P3-7b/P3-7c define it. |
| Postgres | RDS PostgreSQL 16 + required extensions | Least-privilege app role; forced RLS; migration smoke required. |
| Redis | ElastiCache/Redis-compatible endpoint | Required for staging/prod rate-limit parity. |
| Secrets | AWS Secrets Manager + KMS | Secret refs only; no raw values in git or app responses. |
| Domain/TLS | `staging.automatedstructure.com` and `api-staging.automatedstructure.com` or owner-approved equivalents | TLS via ACM/ALB or platform equivalent. |
| Logs/metrics | CloudWatch logs + metrics + alarms | Include backend, worker, ALB, RDS, Redis. |
| Health checks | `/health`, `/live`, `/ready` | ALB health can use live; release smoke must check ready. |
| Boot guard | Active for production-like env | Must pass configured staging policy before promotion. |

Staging restrictions:

- keep email provider mock unless a later P3-5 approved smoke slice supplies concrete values;
- keep live email off;
- keep Stripe/SMS/live scraping off;
- run synthetic CRE demo in mock mode;
- prove auth, RLS, billing gates, send gates, Redis, migrations, and rollback paths.

---

## 6. Environment matrix

| Capability | Local | Staging | Production |
|---|---|---|---|
| Purpose | Developer/demo validation | Production-like proof and smoke | External users / paid pilots only after go/no-go |
| App env | `local` / `development` | `staging` | `production` |
| Docker mode | Dev images + bind mounts | Hardened images | Hardened images |
| DB | Local Postgres/pgvector | RDS/Postgres with least-privilege role | RDS/Postgres with least-privilege role |
| Redis | Optional local profile | Required | Required |
| Secrets | Local placeholders only | Secrets Manager/KMS or staging equivalent | Secrets Manager/KMS required |
| Auth | Mock auth allowed | Real Clerk staging/dev required for cutover smoke | Real Clerk production required |
| Billing | Mock billing | Mock billing unless separate approval | Real Stripe deferred until first-paying-client approval |
| Email | Mock provider only | Mock provider by default; Resend smoke only after P3-5 gates | Live external email only after separate approval/evidence |
| SMS | Disabled | Disabled | Disabled until future approval |
| Live scraping | Disabled | Disabled | Disabled until future approval |
| CI/CD | Local commands | gated release target | owner-approved promotion only |
| Backups | local volume only | backup/restore drill required | backup/restore drill required |
| Observability | logs + tests | CloudWatch/alerts required | CloudWatch/alerts required |

---

## 7. Required owner / operator values

Before P3-7b/P3-7c can become implementation-ready, collect:

1. AWS account ID.
2. AWS region.
3. Deployment platform confirmation: ECS/Fargate vs another approved host.
4. Staging domain/subdomains.
5. API staging URL.
6. Frontend staging URL.
7. TLS/ACM owner.
8. DNS owner.
9. Secrets owner.
10. KMS key owner / key alias.
11. Database owner.
12. RDS instance class/storage/backups policy.
13. Redis/ElastiCache owner and sizing.
14. Backup retention.
15. Target RPO/RTO.
16. Alert recipients / Slack or email destination.
17. Incident commander / escalation owner.
18. CI/CD approval owner.
19. Migration approver.
20. Production cutover approver.
21. Rollback approver.
22. Whether staging may use controlled mock providers and who attests it.
23. Clerk staging values and frontend integration owner.
24. Confirmation that Resend remains disabled in staging until P3-5f+ gates clear.

---

## 8. Implementation slice plan

### P3-7b — Production Dockerfile hardening

- Convert backend/frontend images from dev runtime to production/runtime images.
- Define non-root user, dependency install strategy, no autoreload, deterministic build.
- Add worker command strategy.
- Add image/tag/rollback convention.
- No infrastructure provisioning.

### P3-7c — Staging env / secret template docs

- Create staging config matrix and secret-ref template.
- Define Secrets Manager paths and KMS key references.
- Define RDS/Redis required env values.
- Keep live email, Stripe, SMS, and live scraping off.

### P3-7d — CI/CD plan

- Define image build/push, migrations one-off task, staged rollout, smoke tests, approvals, rollback.
- Add required evidence checklist.
- No cloud changes unless separately approved.

### P3-7e — Staging release only after approval

- Provision or configure staging only after owner supplies required values.
- Run migrations and boot guard.
- Keep provider mock and live email off.

### P3-7f — Staging smoke evidence

- Record health/live/ready, migrations, RLS/tenant isolation, auth, billing/send gates, Redis, worker, rollback, and synthetic mock campaign.
- Attach logs/evidence without secrets.

### P3-7g — Production plan / final production readiness

- Produce final go/no-go packet.
- Require all launch blockers closed or owner-accepted.
- Production cutover requires separate owner approval.

---

## 9. Tests and smoke checks needed later

Staging smoke should include:

- `/health` 200;
- `/live` 200;
- `/ready` ready with DB migrations at head and Redis ok;
- production/staging boot guard passes with expected mock/live restrictions;
- runtime DB role is not SUPERUSER and does not have BYPASSRLS;
- RLS isolation smoke;
- protected API smoke;
- auth smoke with real Clerk staging values when available;
- billing-gate smoke;
- send-gate dry-run smoke, mock-only;
- endpoint rate-limit smoke with Redis 429 and Redis-down 503 behavior;
- worker claim/process smoke with tenant context;
- migration one-off task smoke;
- backup restore drill;
- rollback drill using previous image/task definition;
- no secret/DSN/Redis URL leakage in logs or client responses.

---

## 10. Final verdict

P3-7a inspection is complete.

Deployment remains blocked until the owner/operator values in §7 are supplied and future P3-7 implementation slices are explicitly approved.
