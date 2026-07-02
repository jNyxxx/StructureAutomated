# Operations Runbook

**Purpose:** Combined observability + DevOps runbook - log shape, MVP in-product observability, LangSmith faithfulness logging, post-demo alerts + response steps, local stack, CI, deployment, migration/rollback, backup/restore, environment safety guard, and ops go/no-go checks.
**Source sections:** Master guide §19 (observability/alerts), §20 (DevOps/CI/CD/rollback), §2 (env safety guard).
**Status:** Draft
**Related docs:** [ARCHITECTURE](ARCHITECTURE.md) (stack/infra) - [CLAUDE](../CLAUDE.md) (production boot guard) - [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (CI suites) - [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md) - [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)

---

# Part A - Observability

## A1. Structured log shape

```json
{
  "timestamp": "2026-06-19T00:00:00Z",
  "level": "INFO",
  "service": "backend",
  "environment": "production",
  "request_id": "req_...",
  "correlation_id": "corr_...",
  "tenant_id": "...",
  "actor_id": "...",
  "job_id": "...",
  "event": "campaign.run.started",
  "message": "human readable summary",
  "metadata": {}
}
```

Required across **HTTP -> queue -> worker -> agent -> webhook**: `request_id`, `correlation_id`, `tenant_id` (when applicable), `actor_id` (when applicable), `job_id` (when applicable).

## A2. MVP observability

MVP/demo observability must include in-product views for job/run status, blocked-send reasons, billing-gate state, draft approval state, agent failures, and mock deliverability/outcome summaries.

LangSmith faithfulness logging is required for agent traces, groundedness evidence, prompt-injection results, cost/tokens, and trace URLs.

External Slack/internal alerts are **post-demo**. The first future Slack alert should be deliverability risk: bounce/spam approaching danger thresholds.

## A3. Post-demo required alerts

| Alert | Threshold | Severity |
|---|---|---|
| API 5xx rate | >2% for 5 min | High |
| Login failure spike | >50 failures/10 min/IP range | Medium/High |
| Queue depth/age | >1000 jobs or oldest >15 min | High |
| Dead-letter jobs | Any send/billing/webhook DLQ | High |
| Agent failure rate | >5% in 30 min | Medium |
| Groundedness block spike | >20% drafts blocked | Medium |
| Send duplicate conflict | Any | **Critical** |
| Bounce rate | >=2% campaign/mailbox | High |
| Spam complaints | >=0.1% | High |
| Future Stripe webhook failures | >3 consecutive or unprocessed >15 min | High |
| DB CPU | >80% for 10 min | High |
| DB pool saturation | >80% for 10 min | High |
| AI/provider cost spike | Over daily budget threshold | Medium/High |
| Secrets access anomaly | Unusual Secrets Manager access | **Critical** |

## A4. Runbook response steps

- **Send duplicate conflict (Critical):** halt affected send worker; inspect `send_intents`/`outbound_messages` uniqueness; confirm provider idempotency; resume only after root cause.
- **Secrets access anomaly (Critical):** rotate affected secrets; revoke sessions/grants; review audit + Secrets Manager access logs; incident record.
- **DLQ (send/billing/webhook):** inspect dead-lettered job; replay only after idempotency confirmed; never re-run a send without duplicate check.
- **Future Stripe webhook failures:** verify signature/secret; confirm events stored; re-drive async processing idempotently; reconcile.
- **Bounce/spam over threshold:** auto-pause mailbox/domain ([EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md)); investigate list quality/warm-up.
- **Queue depth/DB saturation:** scale workers/DB; shed non-critical jobs; check for stuck leases.

---

# Part B - DevOps

## B1. Local Docker Compose services

Postgres + pgvector - backend - frontend - worker - n8n - Redis (optional, local rate limiting) - LocalStack (optional, SQS/S3 sim).

Rate-limit backend selection:

- Local/test/default: `RATE_LIMIT_BACKEND=in_memory`.
- Optional local Redis: start `docker compose --profile cache up` and set `RATE_LIMIT_BACKEND=redis` plus `RATE_LIMIT_REDIS_URL=redis://redis:6379/0` for container-local Redis testing.
- Production: `RATE_LIMIT_BACKEND=redis` is required for multi-worker correctness. Real Redis/ElastiCache URL must come from deployment/secrets configuration, not committed files.
- Runtime-smoke evidence: P3-4d proved local Redis counters against a real Redis container, including HTTP 429 behavior, tenant-scoped key isolation, key PII safety, TTL reset, and Redis-down behavior.
- Redis failure/readiness hardening: P3-4e maps Redis/backend counter outages to a sanitized `503 RATE_LIMIT_BACKEND_UNAVAILABLE` response, keeps rate limiting fail-closed, and includes Redis state in `/ready` when `RATE_LIMIT_BACKEND=redis`. P3-4f accepts this rate-limit/abuse-protection track as green. Production cutover still requires deployment-managed Redis/ElastiCache config and staging smoke.

Email provider boundary / future provider config:

- Current safe default: `EMAIL_PROVIDER=mock` and `LIVE_EMAIL_SENDING_ENABLED=false`.
- P3-5b registers only the network-free mock adapter; provider names fail closed until a later owner-approved slice adds a real adapter.
- P3-5c design requires provider credentials and webhook signing secrets to be referenced by secret refs only and loaded from AWS Secrets Manager/KMS in production.
- P3-5e owner approval (2026-06-28): **Resend** selected as the pilot email provider; sending subdomain `outreach.automatedstructure.com`; conservative first-pilot caps (tenant 10/hr·50/day, campaign 50/day, mailbox 25/day); webhook events normalized to `delivered`/`bounced`/`complained`/`deferred`/`failed`/`unsubscribed` with signature verify + idempotency required (no open/click tracking). Real sending stays disabled (`EMAIL_PROVIDER=mock`, `LIVE_EMAIL_SENDING_ENABLED=false`); the Resend adapter is **not** built. See [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §2 and [evidence/phase-3-5e-owner-approval-resend-roadmap.md](evidence/phase-3-5e-owner-approval-resend-roadmap.md).
- P3-5j scope correction (2026-06-29): Resend is **transactional/opted-in only** — NOT cold outreach. Cold outreach routes to a future dedicated mailbox-pool manager (mocked for MVP). `send_layer` guard in `ResendEmailSendProvider` rejects cold_outreach intent with `COLD_OUTREACH_NOT_ALLOWED` (422). See [evidence/phase-3-5j-dual-sending-layer-scope-correction.md](evidence/phase-3-5j-dual-sending-layer-scope-correction.md).

#### Emergency stop — sending layers

**Transactional layer (Resend):**
Set `LIVE_EMAIL_SENDING_ENABLED=false`. Takes effect on next request.
Contact: William (email + ops).
RTO: < 5 minutes (config flag, no deploy required).

**Cold outreach layer (future mailbox-pool manager):**
`LIVE_COLD_SENDING_ENABLED=false` — REQUIRED before that layer goes live.
Not yet implemented. Hard blocker for the mailbox-pool manager phase.

Both kill switches must be documented with owner contact and RTO before
any live sending is enabled on either layer.
- Production provider cutover must verify sending domain DNS, webhook signatures, tenant/campaign/mailbox/provider caps, legal footer/unsubscribe copy, and internal-only smoke evidence before any external recipient delivery.

## B1b. Local mock demo login

For local/mock development and demo sessions, the sign-in page includes a "Continue with Demo Account" button. No real Clerk credentials required.

**Prerequisites:**
- Local stack running (`docker compose up` or backend on port 8000 + frontend on port 3000 separately).
- `APP_ENV=local` (backend) — ensures mock auth is allowed.
- `NEXT_PUBLIC_CLERK_MOCK_MODE=true` or `NODE_ENV` is not `"production"` (frontend).

**Steps:**
1. Navigate to `http://localhost:3000/login`.
2. Click "Continue with Demo Account".
3. Browser redirects to `/dashboard` as `owner@example.com` (tenant `22222222-2222-2222-2222-222222222222`, role `owner`).
4. Session persists across page refreshes via localStorage (`as_mock_session=1`).
5. To sign out: any sign-out action clears localStorage and returns to signed-out state.

**Demo identity:** token `token-sentinel` / user `11111111-1111-1111-1111-111111111111` / tenant `22222222-2222-2222-2222-222222222222` / email `owner@example.com` / role `owner`.

**Safety:** Demo button does not appear in production. `isLocalMockAuthAllowed()` blocks mock auth when `NODE_ENV === "production"` without explicit mock flag. Boot guard prevents `LocalMockClerkVerifier` from running in production. See [evidence/phase-3-demo-2-local-mock-auth-readiness.md](evidence/phase-3-demo-2-local-mock-auth-readiness.md).

## B1c. Fresh-volume local bootstrap

On a brand-new/empty local Postgres volume (e.g. after `docker compose down -v`, or a fresh clone), run these in order before using the demo login above — no manual SQL required:

1. `docker compose up -d --build`
2. `docker compose exec backend alembic upgrade head`
3. `docker compose exec backend python -m app.scripts.bootstrap_local_demo` — creates the demo tenant (`22222222-2222-2222-2222-222222222222`), owner user (`11111111-1111-1111-1111-111111111111`, `owner@example.com`), membership, `mvp_mock` billing subscription, and a safe compliance profile (live sending/SMS off). Idempotent — safe to re-run; prints `CREATED` or `SKIPPED (already_exists)` per entity.
4. `docker compose exec backend python -m app.scripts.seed_local_grounding` — adds the grounding document drafts need to reach `status: "generated"` instead of `needs_regeneration`. Depends on step 3 having run first; fails closed with `SeedPreconditionError` otherwise.

Both scripts refuse to run unless `APP_ENV` is `local`/`development`/`demo`.

To smoke-test the fresh-volume path without touching your normal dev database, run the same commands with an isolated Compose project name so a separate, disposable volume is used instead of `automatedstructure_db_data`:

```
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose down --remove-orphans
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose up -d --build
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose exec backend alembic upgrade head
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose exec backend python -m app.scripts.bootstrap_local_demo
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose exec backend python -m app.scripts.seed_local_grounding
# ... verify, then tear down the disposable volume:
COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke docker compose down -v --remove-orphans
```

Stop the normal dev stack first (or expect host port collisions on 8000/3000/5432, since `docker-compose.yml` maps fixed host ports) — both projects can't bind the same ports at once. See [evidence/phase-4-fresh-volume-bootstrap.md](evidence/phase-4-fresh-volume-bootstrap.md).

## B2. CI jobs (all must pass)

1. Backend lint/type.
2. Frontend lint/type.
3. Backend unit.
4. Frontend tests.
5. Migration up/down smoke.
6. RLS isolation.
7. API contract/schema.
8. Agent safety eval corpus (mock).
9. Secret scan.
10. Dependency vuln scan.
11. Docker build.
12. Docker smoke test.

CI **blocks** secrets, failing tests, and migration drift.

## B3. Deployment pipeline

P3-7a readiness inspection (2026-06-28): current Dockerfiles are local/dev-oriented (`uvicorn --reload`, `next dev`, bind mounts in Compose), CI is green-shaped for lint/type/test/build/migration smoke, backend boot guard/readiness are strong, Redis/rate-limit track is accepted, and P3-5e Resend direction is recorded. Staging/production work remains blocked on owner/operator values for AWS account/region, deployment platform, domains/TLS, Secrets Manager/KMS, RDS, Redis, backups, alerts, CI/CD approvals, migration/rollback owners, and production cutover approver. See [evidence/phase-3-7a-deployment-ops-readiness-plan.md](evidence/phase-3-7a-deployment-ops-readiness-plan.md).

P3-7b production Dockerfile hardening (2026-06-28): added production-specific `backend/Dockerfile.prod` and `frontend/Dockerfile.prod`, preserved dev Dockerfiles/Compose, hardened backend/frontend `.dockerignore`, and enabled Next standalone output for the production frontend image. Backend/frontend code gates passed. P3-7b-verify cleared the Docker build blocker: Docker Desktop/Linux engine ran on Docker 29.5.3 and both production images built locally. The frontend build required a minimal `frontend/package-lock.json` npm 10 sync so Docker `npm ci` is deterministic. See [evidence/phase-3-7b-production-dockerfile-hardening.md](evidence/phase-3-7b-production-dockerfile-hardening.md) and [evidence/phase-3-7b-production-docker-build-smoke.md](evidence/phase-3-7b-production-docker-build-smoke.md).

P3-7c staging environment + secret template (2026-06-28): docs-only staging config map created in [STAGING_ENVIRONMENT_TEMPLATE.md](STAGING_ENVIRONMENT_TEMPLATE.md). It groups backend, frontend, worker, migration, database, Redis, Clerk, mock billing, Resend-disabled, and observability variables; defines secret-ref naming under `/automatedstructure/staging/...`; records staging preflight/boot-guard requirements; and keeps Resend/live email, Stripe, SMS, and live scraping disabled. See [evidence/phase-3-7c-staging-env-secret-template.md](evidence/phase-3-7c-staging-env-secret-template.md).

P3-6a Stripe / real billing owner decision packet (2026-06-28): docs-only decision packet created before any Stripe implementation. Real billing remains deferred until owner answers provider/mode/pricing/entitlement/webhook/dunning/refund/chargeback/config/owner decisions and approves a specific P3-6 implementation slice. No Stripe SDK/API call, checkout, webhook, money movement, deployment, or production enablement was added. See [evidence/phase-3-6a-stripe-billing-owner-decision-packet.md](evidence/phase-3-6a-stripe-billing-owner-decision-packet.md).

P3-6b Stripe config / secret-readiness contract (2026-06-28): docs-only contract created. Defines Stripe refs, URL separation, test-first mode defaults, product/price mapping needs, readiness states (`config_ready`, `test_billing_ready`, `money_ready`, `production_billing_ready`), central gate invariants, webhook readiness, hard stops, and remaining owner answers. It adds no Stripe SDK/API call, checkout, webhook, real billing, money movement, deployment, or production enablement. See [evidence/phase-3-6b-stripe-config-secret-readiness-contract.md](evidence/phase-3-6b-stripe-config-secret-readiness-contract.md).

P3-6c Stripe billing owner defaults (2026-06-28): docs-only safe defaults recorded. Stripe is the future billing provider direction, while mock billing remains default. Defaults cover test-first mode, manual first-pilot option, self-serve checkout disabled by default, placeholder internal plans, 14-day trial, 7-day failure grace, owner/operator fallback roles, and remaining exact values. See [evidence/phase-3-6c-stripe-owner-defaults.md](evidence/phase-3-6c-stripe-owner-defaults.md).

P3-6d Stripe webhook verification foundation (2026-06-29): fail-closed webhook verifier, event normalizer, idempotency boundary, route skeleton, config placeholders, and staging/production boot-guard checks added. Default route behavior remains fail-closed until secret resolution is approved. No checkout, billing portal, provider API call, billing-state mutation, or money movement was added. See [evidence/phase-3-6d-stripe-webhook-verification-foundation.md](evidence/phase-3-6d-stripe-webhook-verification-foundation.md).

P3-6e Stripe checkout / billing portal skeleton (2026-06-29): fail-closed provider boundary and route skeletons added for future test-mode checkout and portal sessions. Defaults keep `STRIPE_CHECKOUT_ENABLED=false` and `STRIPE_BILLING_PORTAL_ENABLED=false`; enabled staging/production config now fails closed without required refs/URLs. No session creation, provider API call, billing-state mutation, or money movement was added. See [evidence/phase-3-6e-stripe-checkout-portal-skeleton.md](evidence/phase-3-6e-stripe-checkout-portal-skeleton.md).

P3-6f-prep Stripe test-mode webhook smoke preparation (2026-06-30): required concrete values (test secret refs, smoke approver, emergency-stop operator, Stripe CLI), test-mode gates, 13-step webhook smoke scenario, 10 hard stop conditions, evidence contract for P3-6h smoke doc, and remaining slices P3-6g through P3-6k defined. Actual smoke (P3-6h) remains blocked on secret resolution wiring (P3-6g) and named smoke approver attestation. See [evidence/phase-3-6f-prep-stripe-test-mode-smoke.md](evidence/phase-3-6f-prep-stripe-test-mode-smoke.md).

P3-8a launch readiness dashboard (2026-06-30): consolidated blocker and readiness document created for the boss (William). Demo is READY. 38 open blockers documented across infrastructure/staging, Clerk, Stripe, Resend, cold outreach, and legal tracks — all require owner/operator action before any real-provider or staging work can proceed. See [evidence/phase-3-8a-launch-readiness-dashboard.md](evidence/phase-3-8a-launch-readiness-dashboard.md).

P3-Final boss handoff package (2026-06-30): final Phase 3 handoff created. Phase 3 mock/demo readiness complete. Covers demo startup instructions, browser flow, complete/not-live/safety summaries, open blocker summary, recommended next paths, and boss-facing message for William. See [evidence/phase-3-final-boss-handoff-package.md](evidence/phase-3-final-boss-handoff-package.md).

P3-Audit final requirements/architecture compliance audit (2026-06-30): final read-only audit complete. Result: PASS for Phase 4 planning only. Verified Phase 3 against locked architecture, owner decisions, safety/compliance, local/mock demo readiness, disabled-provider constraints, CI/Docker gates, and Phase 4 entry readiness. Backend Ruff/Black/mypy/731 pytest PASS; frontend npm ci/lint/typecheck/141 tests/build PASS; backend/frontend production Docker builds PASS with `p3-audit-local` tags. See [evidence/phase-3-final-requirements-architecture-audit.md](evidence/phase-3-final-requirements-architecture-audit.md).

P3-Audit-Cleanup final handoff reference cleanup (2026-06-30): corrected the stale commit reference in the final handoff package. P3-Final package created at `9ec8d99`; final audited Phase 3 baseline is `747db3f`. Docs-only; no provider, production, deployment, registry, secret, billing, SMS, or live scraping behavior changed.

P4-0 staging and first-pilot entry plan (2026-06-30): Phase 4 opened as planning-only staging/pilot readiness. The required next operational inputs are AWS account/region, registry target, deployment platform, staging frontend/API domains, DNS/TLS owner, runtime config custody, RDS/Postgres config, Redis/ElastiCache config, Clerk staging values, Stripe test-mode smoke values, Resend transactional smoke values, alert recipients, deployment/migration/rollback approvers, emergency-stop owner, deliverability owner, and later production cutover approver. P4-0 adds no deployment, registry push, provider enablement, billing money movement, SMS, or live scraping. See [PHASE_4_IMPLEMENTATION_PLAN](PHASE_4_IMPLEMENTATION_PLAN.md) and [evidence/phase-4-0-staging-pilot-entry-plan.md](evidence/phase-4-0-staging-pilot-entry-plan.md).

P4-1 staging infrastructure values intake (2026-06-30): owner/operator intake packet created. Current staging readiness remains BLOCKED: AWS account ID, region, registry target, staging domains, DNS/TLS owner, RDS/Redis sizing, migration/deployment/rollback approvers, alert recipients, incident owner, emergency-stop owner, monitoring target, worker service decision, Clerk staging values, and approved staging auth mode are not locked. Safe defaults such as staging-first, commit-SHA tags, no latest-only deployment, Postgres 16-compatible RDS, managed Redis, AWS Secrets Manager + KMS, and provider flags disabled are recommendations only. Do not proceed to P4-2/P4-4/P4-5 until required values are LOCKED or explicitly deferred. See [evidence/phase-4-1-staging-infrastructure-values-intake.md](evidence/phase-4-1-staging-infrastructure-values-intake.md).

P4-1b owner response tracker (2026-06-30): decision matrix added for William/operator answers. AWS account/region plus config/KMS decisions unlock P4-2; registry target unlocks P4-4; Clerk values or approved mock-staging auth unlock P4-3; staging domains plus DNS/TLS and approvers unlock later P4-5/P4-6; Stripe and Resend values unlock later smoke slices only. Until answers are LOCKED or explicitly DEFERRED, safe work is limited to local demo polish, boss walkthrough script, dependency audit triage plan, monitoring/alerts planning, first-pilot readiness checklist, and docs cleanup. See [evidence/phase-4-1b-owner-response-tracker.md](evidence/phase-4-1b-owner-response-tracker.md).

P4-Demo-Walkthrough boss demo script (2026-06-30): docs-only walkthrough and QA checklist created for William's local/mock review. Covers objective, pre-demo setup, local stack URLs, demo login, health/readiness checks, full walkthrough path (login → dashboard → contacts/prospects → campaign → draft/evidence → review → human approval → send-gate dry run → mock send intent → outbound record → audit → billing/access gates → compliance → deliverability/outcomes → sign out/in), safety proof, troubleshooting, QA checklist, and boss-facing close. No code changes, deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping. See [evidence/phase-4-demo-walkthrough-script.md](evidence/phase-4-demo-walkthrough-script.md).

P4-DepAudit-Plan dependency audit triage (2026-06-30): docs-only audit triage created before any package updates. Current frontend npm audit evidence records 10 vulnerability records (4 moderate, 5 high, 1 critical): Next.js/PostCSS runtime group, eslint-config-next/@next/eslint-plugin-next/glob lint group, and Vitest/Vite/Vite-node/@vitest/mocker/esbuild test-tooling group. No `npm audit fix`, `npm update`, install, package version edit, lockfile edit, deployment, registry push, or provider enablement was performed. Boss demo remains allowed for controlled local/mock review; staging/production require fixes or explicit owner/security risk acceptance. See [evidence/phase-4-dependency-audit-triage-plan.md](evidence/phase-4-dependency-audit-triage-plan.md) and [evidence/phase-4-dependency-audit-raw.json](evidence/phase-4-dependency-audit-raw.json).

P4-DepAudit-Fix-1 safe dev dependency fixes (2026-06-30): targeted frontend dev/test package fix completed. Updated `vitest` `^2.1.0` → `^3.2.6` and added/pinned `vite` `^6.4.3` to clear the Vitest/Vite/esbuild audit group without changing app source, backend, Dockerfiles, workflows, deployment config, provider code, or Next.js runtime. Frontend gates passed: `npm ci`, lint, typecheck, 141 tests, and `next build`. Audit reduced 10 → 5; critical reduced 1 → 0. Remaining findings: Next.js runtime/PostCSS and Next ESLint/glob lint chain. Boss demo remains allowed; staging/production remain blocked until remaining findings are fixed or formally accepted and owner/operator values are locked. See [evidence/phase-4-dependency-audit-fix-1.md](evidence/phase-4-dependency-audit-fix-1.md) and [evidence/phase-4-dependency-audit-after-fix-1.json](evidence/phase-4-dependency-audit-after-fix-1.json).

P4-DepAudit-Fix-2 remaining dependency audit assessment (2026-06-30): BLOCKED. Current `next` and `eslint-config-next` are already at `14.2.35`, the latest same-major 14.x versions found. Candidate fixes require major framework-aligned upgrades to Next/eslint-config-next 15.x or 16.x, which are outside Fix-2 scope. No package files were changed, no gates were rerun, and no deployment/provider/runtime behavior changed. Boss demo remains allowed; staging/production remain blocked. Next dependency step is P4-DepAudit-Fix-3 framework upgrade planning or formal owner/security risk acceptance. See [evidence/phase-4-dependency-audit-fix-2.md](evidence/phase-4-dependency-audit-fix-2.md).

P4-DepAudit-Fix-3-Plan framework upgrade approval plan (2026-06-30): docs-only plan created. Recommended path is P4-DepAudit-Fix-3a: owner-approved Next 15.5.16+ controlled upgrade attempt with aligned `eslint-config-next` 15.x, React 18 preserved initially, Node 20 preserved, and full frontend gates plus browser smoke and frontend production Docker build. Next 16 is escalation only if Next 15 does not clear findings or William explicitly approves the larger jump. No package, source, Dockerfile, workflow, deployment, provider, billing, SMS, or live scraping changes were made. Boss demo remains allowed; staging/production remain blocked until findings are fixed or formally accepted and owner/operator values are locked. See [evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md](evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md).

P4-FirstPilot-Readiness checklist (2026-07-01): docs-only first paying-client readiness checklist created. It defines limited pilot scope, required pre-client gates, client onboarding fields, demo-to-pilot gaps, go/no-go criteria, hard stops, and William approval requirements. First client remains a limited pilot, not a public launch. Manual approval remains required for AI drafts; cold outreach, Stripe live money movement, SMS, and live scraping remain blocked unless separately approved. Boss demo remains allowed; staging/production remain blocked. See [evidence/phase-4-first-pilot-readiness-checklist.md](evidence/phase-4-first-pilot-readiness-checklist.md).

P4-Monitoring-Alerts-Plan (2026-07-01): docs-only monitoring, alerting, incident ownership, and rollback plan created for staging/pilot readiness. It defines staging-first monitoring scope, required alert categories, owner roles, SEV-1 through SEV-4 levels, staging smoke observability checks, rollback procedures, hard stops, and William-facing questions. No deployment, package, source, config, secret, provider, billing, SMS, live scraping, or production change. Boss demo remains allowed; staging/production remain blocked until alert recipients, incident owner, deployment/migration/rollback approvers, emergency-stop owner, monitoring target, and log retention are locked. See [evidence/phase-4-monitoring-alerts-incident-plan.md](evidence/phase-4-monitoring-alerts-incident-plan.md).

P4-LocalReadiness-Closeout / Resume (2026-07-01): docs-only local readiness closeout package finalized after an initial partial attempt was interrupted by a devspace session termination. William's current decision is recorded: AWS, staging, deployment, registry, and provider setup remain paused; production waits for the first real client; local hardening, QA, docs, demo prep, and first-client prep may continue. Evidence records backend Ruff/Black/mypy/pytest PASS; frontend `npm ci`, lint, typecheck, 141 tests, and build PASS; `npm audit` on `master` still blocked by known findings until `p4/next15-upgrade` is approved/merged; local route smoke PASS; Docker compose full-stack boot evidence incomplete; send-gate, billing/access, compliance, webhook fail-closed, and provider-boundary QA documented; first-client onboarding runbook created. Boss demo remains allowed with manual browser click-through recommended. See [evidence/phase-4-local-readiness-closeout.md](evidence/phase-4-local-readiness-closeout.md), [evidence/phase-4-sendgate-compliance-qa.md](evidence/phase-4-sendgate-compliance-qa.md), and [evidence/phase-4-first-client-onboarding-runbook.md](evidence/phase-4-first-client-onboarding-runbook.md).

P4-LocalE2E-Completion (2026-07-01): local full-stack E2E hardening attempt recorded as BLOCKED. Backend Ruff/Black/mypy/pytest pass; frontend `npm ci`, lint, typecheck, 141 tests, and build pass; route smoke for core demo pages returns 200; backend/frontend route inventories align for local/mock MVP areas. No source, package, Dockerfile, workflow, `.env`, deployment, provider, staging, or production changes were made. Remaining blockers: Docker compose cannot be verified because Docker Desktop/Linux daemon is unavailable, `/health`/`/live`/`/ready` through compose were not run, `npm audit` still fails on `master` until William approves merging `p4/next15-upgrade`, and manual browser click-through remains recommended before the boss demo. Boss demo remains allowed with caveats; staging remains paused by William; production waits for the first real client. See [evidence/phase-4-local-e2e-completion.md](evidence/phase-4-local-e2e-completion.md).

P4-LocalDockerE2E-Retry (2026-07-01): local Docker full-stack E2E retry recorded as BLOCKED. Docker Desktop/Linux engine is available; compose build/start passed; DB is healthy; backend/frontend/n8n/worker containers are up; `/health`, `/live`, and `/ready` pass; frontend route smoke returns 200 for all required local demo routes; local mock auth returns 401 without auth and 200 with mock token + tenant header. Full happy-path E2E is blocked because `POST /api/v1/campaigns` returns 500 in `backend/app/repositories/campaign_repo.py` (`UUID` object has no attribute `id`). No source fix was applied because this requires a separate source-fix slice. No package, source, Dockerfile, workflow, `.env`, registry, deployment, provider, staging, production, live sending, Stripe money movement, SMS, or live scraping change occurred. Boss demo remains allowed only with caveats. See [evidence/phase-4-local-docker-e2e-retry.md](evidence/phase-4-local-docker-e2e-retry.md).

P4-LocalDockerE2E-Fix-1-CampaignCreate (2026-07-01): backend source fix and Docker E2E retry recorded as PARTIAL COMPLETE. Fixed `POST /api/v1/campaigns` 500 by mapping explicit campaign columns through `Result.mappings()` instead of scalar UUIDs in `CampaignRepository`. Also fixed idempotency lookup row mapping exposed by campaign-create replay. Added regression tests for both mappers. Backend Ruff/Black/mypy/pytest PASS; frontend lint/typecheck/141 tests/build PASS; Docker compose rebuild PASS; `/ready`, `/health`, `/live` PASS; frontend route smoke PASS; campaign create now returns 201 and campaign list returns complete campaign objects. Full happy-path E2E remains blocked at the next write path: `POST /api/v1/imports/contacts` returns 500 from `contact_repo.py` scalar UUID row mapping. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, live sending, Stripe money movement, SMS, or live scraping change occurred. Boss demo remains allowed only with caveats. See [evidence/phase-4-local-docker-e2e-fix-1-campaign-create.md](evidence/phase-4-local-docker-e2e-fix-1-campaign-create.md).

P4-LocalDockerE2E-Fix-2-ContactImport (2026-07-02): backend source fix and Docker E2E retry recorded as PARTIAL COMPLETE. Fixed `POST /api/v1/imports/contacts` 500 by mapping explicit contact import/contact/import-row columns through `Result.mappings()` instead of scalar UUIDs in `ContactImportRepository`. Added regression test. Backend Ruff/Black/mypy/pytest PASS; frontend lint/typecheck/141 tests/build PASS; Docker compose rebuild PASS; `/ready`, `/health`, `/live` PASS; frontend route smoke PASS; contact import now returns 201 and a complete safe import summary; contact read returns 200; campaign-contact selection returns 201. Full happy-path E2E remains blocked at the next write path: `POST /api/v1/drafts/generate` returns 500, likely the next same-pattern row-mapping issue in `draft_repo.py`. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, live sending, Stripe money movement, SMS, or live scraping change occurred. Boss demo remains allowed only with caveats. See [evidence/phase-4-local-docker-e2e-fix-2-contact-import.md](evidence/phase-4-local-docker-e2e-fix-2-contact-import.md).

P4-LocalDockerE2E-Fix-3-DraftGeneration (2026-07-02): backend source fix and Docker E2E retry recorded as PARTIAL COMPLETE. Fixed `POST /api/v1/drafts/generate` 500 by mapping explicit draft/evidence, safety result, and review item columns through `Result.mappings()` instead of scalar mapping in the draft-generation path. Added repository row-mapping regression tests. Backend Ruff/Black/mypy/pytest PASS; frontend lint/typecheck/141 tests/build PASS; Docker compose rebuild PASS; `/ready`, `/health`, `/live` PASS; frontend route smoke PASS; draft generation now returns 201 and a complete draft object; draft evidence read returns 200. Full approve/send happy path remains caveated because current local data produces a groundedness fail-closed draft with status `needs_regeneration`, so no pending review item/sendable draft was reached. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, Stripe money movement, SMS, or scraping change occurred. Boss demo remains allowed only with caveats. See [evidence/phase-4-local-docker-e2e-fix-3-draft-generation.md](evidence/phase-4-local-docker-e2e-fix-3-draft-generation.md).

P4-LocalDockerE2E-Fix-4-GroundedHappyPathSeed (2026-07-02): backend source fix, local/mock seed, and full Docker E2E verification recorded as COMPLETE. Added `docker compose exec backend python -m app.scripts.seed_local_grounding` — a local/mock-only, env-guarded (refuses outside `local`/`development`/`demo`), idempotent seed that ingests one clearly-labeled `LOCAL DEMO MOCK` knowledge document through the existing gated `RAGGroundingService.add_document` path. This gives the local tenant valid, citable grounding evidence so draft generation reaches `status: "generated"` instead of the groundedness fail-closed `needs_regeneration`. Also fixed two newly-discovered same-pattern row-mapping bugs that surfaced once the send-gate and audit-read paths were exercised in Docker for the first time: `backend/app/repositories/sending_repo.py` (blocked `POST /api/v1/send-gate/dry-run`) and `backend/app/audit/repository.py` (blocked `GET /api/v1/audit-events`), both fixed with the same explicit-columns + `Result.mappings()` pattern as fix-1/2/3. Also extended `knowledge_repo.py`'s row-mapping fix to every method (not just the two write paths) since `list_chunks_for_grounding`/`get_research_artifact_for_contact` are on the same path. Backend Ruff/Black/mypy/pytest PASS (751 tests); frontend lint/typecheck/141 tests/build PASS; Docker compose rebuild PASS; `/ready`, `/health`, `/live` PASS; frontend route smoke PASS (`/review-queue`, `/billing`, `/settings/suppression`, `/settings/compliance`). Full local Docker happy path now verified end to end: contact import → campaign create → contact selection → seed → draft generation (`generated`) → evidence read → review queue → human approval → send-gate dry run (`passed`) → mock send intent (`mock_sent`) → outbound read → audit trail, all against the live stack. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, Stripe money movement, SMS, or scraping change occurred; no gate was weakened. Boss demo allowed. See [evidence/phase-4-local-docker-e2e-fix-4-grounded-happy-path-seed.md](evidence/phase-4-local-docker-e2e-fix-4-grounded-happy-path-seed.md).

P4-RepositoryRowMapping-Hardening (2026-07-02): repo-wide row-mapping hardening sweep recorded as COMPLETE. Scanned every file in `backend/app/repositories/` for the scalar-RETURNING-under-AsyncConnection bug class fixed in fix-1/2/3/4; fixed 9 previously-unfixed files (`billing_repo.py`, `compliance_repo.py`, `support_access_repo.py`, `membership_repo.py`, `user_repo.py`, `tenant_repo.py`, `followup_repo.py`, `outcomes_repo.py`, `research_repo.py` — 46 call sites) with the identical explicit-columns + `Result.mappings()` pattern. Two findings were more severe than routine mechanical fixes: `membership_repo.get_for_user_and_tenant` and `user_repo.get_by_identity` sit on the real (non-mock) Clerk auth path via `backend/app/auth/managed.py` and would have crashed on any real login with an existing user/membership — entirely masked locally because mock auth never touches these repositories; `research_repo.get_contact` had no mapper at all and would have crashed `process_research_job` (the research worker's main entrypoint) on every real invocation with an existing contact. Confirmed 2 outcomes-repo methods already safe (no `.scalars()` call) and 2 methods (`tenant_repo.get_current`, `membership_repo.list_for_current_tenant`) confirmed dead code (documented with deferred comments, left unfixed). Added 41 new regression tests (50 total in `test_repository_row_mapping.py`) plus an additive test-harness extension for multi-query and cursor-pagination methods. Backend Ruff/Black/mypy/pytest PASS (792 tests); frontend lint/typecheck/141 tests/build PASS; Docker compose rebuild PASS; `/ready`, `/health`, `/live` PASS; 10-route frontend smoke PASS; 5 of the 9 fixed repositories additionally live-verified against real Postgres (billing subscription, compliance profile, suppressions list, tenant read, memberships list) with zero regressions. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, Stripe money movement, SMS, or scraping change occurred; no gate was weakened. Boss demo allowed. See [evidence/phase-4-repository-row-mapping-hardening.md](evidence/phase-4-repository-row-mapping-hardening.md).

P4-FinalManualDemoSmoke (2026-07-02): final local/mock demo smoke evidence recorded the core Docker demo flow as passing through contact import, campaign create, grounded draft generation, review approval, send-gate, mock send, outbound record, audit trail, billing/access, compliance/suppressions, deliverability, and outcomes. It also found the final logout -> login blocker: `POST /auth/logout` revoked the fixed local mock session ref, and future demo sessions returned `401 AUTH_SESSION_REVOKED`. This blocker is closed by P4-LocalMockAuthSessionCycle-Fix. See [evidence/phase-4-final-manual-demo-smoke.md](evidence/phase-4-final-manual-demo-smoke.md).

P4-LocalMockAuthSessionCycle-Fix (2026-07-02): local/mock logout -> re-login fixed. The frontend now creates a fresh local demo token per sign-in and the backend local mock verifier maps each token/session id to a distinct provider session ref. Logout revokes only the current local mock session; reusing that token is still rejected, while a fresh demo login succeeds without backend restart. Backend and frontend gates passed, Docker health/readiness passed, container auth-cycle regressions passed, and abbreviated local demo route smoke passed. Production Clerk/JWT auth is unchanged; no deployment, registry push, provider enablement, billing money movement, SMS, live scraping, package change, or real `.env` change occurred. Boss demo is fully allowed for local/mock flow. See [evidence/phase-4-local-mock-auth-session-cycle-fix.md](evidence/phase-4-local-mock-auth-session-cycle-fix.md).

P4-FreshVolumeBootstrap (2026-07-02): committed local fresh-volume demo tenant bootstrap added, closing the manual-SQL gap flagged by P4-LocalDockerE2E-Fix-4. `app/scripts/bootstrap_local_demo.py` idempotently provisions the demo tenant/user/membership/`mvp_mock` subscription/compliance profile through `tenant_session` (no raw connections, no RLS bypass); four small repository create/lookup methods were added to support it. Verified on a genuinely fresh, isolated Docker volume (`COMPOSE_PROJECT_NAME=automatedstructure_fresh_smoke`): migrate -> bootstrap (idempotent across two runs) -> `seed_local_grounding` (now succeeds) -> full grounded happy-path E2E (import -> campaign -> draft `generated` -> review -> approve -> send-gate `passed` -> mock send -> full audit trail). Backend gates passed (800 tests); frontend gates passed (142 tests, build 27 routes). The normal dev stack's volume was untouched throughout. No gate weakened; no package, `.env`, deployment, provider, staging, production, or `p4/next15-upgrade` change occurred. Boss demo allowed. See §B1c above and [evidence/phase-4-fresh-volume-bootstrap.md](evidence/phase-4-fresh-volume-bootstrap.md).

P4-LocalE2E-SmokeScript (2026-07-02): repeatable local Docker E2E smoke command added. `docker compose exec backend python -m app.scripts.local_e2e_smoke` now runs bootstrap -> grounding seed -> login/session -> contact import/readback -> campaign create -> contact selection -> grounded draft -> evidence read -> review queue -> approve -> send-gate dry run -> mock send -> outbound readback -> audit trail -> logout/re-login. The script refuses outside `local`/`development`/`demo`, prints per-step PASS/FAIL output, and was verified 5 consecutive times against the normal long-lived dev volume. This slice also fixed `bootstrap_local_demo.py` identity-provider drift (`local_mock` -> `clerk`) and updated replay handling so state is recovered through GET/list lookups when idempotency responses intentionally return `resource: None`. Backend gates passed (816 tests); frontend gates passed (142 tests, build 27 routes); Docker health/readiness passed. No package, `.env`, Dockerfile, workflow, registry, deployment, provider, staging, production, billing, live sending, SMS, scraping, or `p4/next15-upgrade` change occurred. Boss demo allowed. See [evidence/phase-4-local-e2e-smoke-script.md](evidence/phase-4-local-e2e-smoke-script.md).

P4-LocalLoadStabilitySmoke (2026-07-02): local-only backend load/stability smoke added. `docker compose exec -T backend python -m app.scripts.local_stability_smoke` runs one local E2E precheck, repeated health/readiness checks, repeated auth logout/re-login cycles, a small parallel local mock auth probe, clean 4xx failure checks, repeated full E2E runs, and outbound/audit readbacks. It refuses outside `local`/`development`/`demo`, uses local/mock auth only, and requires review approval, send-gate, mock send, outbound, audit, and logout/re-login steps to be present. Docker result: `STABILITY PASSED (passes=77 failures=0 requests=188 server_500s=0 exceptions=0 clean_failures=2 e2e_runs=4)`. Backend and frontend gates passed; Docker health/readiness and local E2E smoke passed. No package, `.env`, Dockerfile, compose, workflow, registry, deployment, provider, staging, production, live send, Stripe money movement, SMS, scraping, or `p4/next15-upgrade` change occurred. Boss demo allowed. See [evidence/phase-4-local-load-stability-smoke.md](evidence/phase-4-local-load-stability-smoke.md).

P4-BossClientDemoPacket (2026-07-03): docs-only boss/client demo packet added at [demo/BOSS_CLIENT_DEMO_PACKET.md](demo/BOSS_CLIENT_DEMO_PACKET.md). It explains AutomatedStructure in plain English, marks local/mock demo, Docker E2E, fresh-volume bootstrap, and stability smoke as READY, marks staging as PAUSED, production as WAITING FOR FIRST REAL CLIENT, `p4/next15-upgrade` as WAITING FOR WILLIAM APPROVAL, and real providers as DISABLED. It includes the 16-step boss demo script, talking points, recent evidence summary, intentionally blocked live capabilities, remaining William approvals, first-client onboarding checklist, recommended next decisions, and safe local demo commands. No source, package, `.env`, deployment, provider, staging, production, live sending, billing money movement, SMS, scraping, or `p4/next15-upgrade` change occurred. Boss demo packet ready.

P3-7d CI/CD release pipeline plan (2026-06-28): docs-only release plan created. Current CI already covers backend Ruff/Black/mypy/pytest/migration smoke, frontend lint/typecheck/test/build, gitleaks, and pre-commit. Future implementation should add `npm ci`, production Docker image builds, immutable SHA tags, registry push only after approval, migration one-off tasks, staging/production GitHub Environment approvals, smoke evidence capture, and rollback gates. No workflow implementation yet. See [evidence/phase-3-7d-cicd-release-pipeline-plan.md](evidence/phase-3-7d-cicd-release-pipeline-plan.md).

P3-7d-impl CI validation gates (2026-06-28): validation-only workflow hardening implemented. CI now uses `npm ci`, keeps backend/frontend/secret-scan/pre-commit checks, adds changed-file safety guards, and builds backend/frontend production Docker images locally with commit-SHA validation tags only. No release job, registry upload, AWS configuration, staging release, production release, live-provider behavior, or money/SMS/scraping enablement was added. See [evidence/phase-3-7d-ci-validation-gates-implementation.md](evidence/phase-3-7d-ci-validation-gates-implementation.md).

P3-7e-plan staging release runbook (2026-06-30): docs-only staging runbook and go/no-go checklist created. Defines 20 staging prerequisites (all open), image/build procedure (commit-SHA tags, no latest-only, no registry push until approved), migration one-off task procedure (alembic upgrade head; expected head `00022_platform_admin_role`; migration-approver sign-off required before backend starts), service startup order (migration → backend → frontend; worker disabled by default; boot guard must pass; `/ready` must be fully ok), 21-item staging smoke checklist, 18 hard stop conditions, rollback plan (previous image tag/task def retention; forward-fix default; no auto-DB-rollback unless snapshot exists), and required evidence bundle (26 items) for real staging deploy. No deployment, registry push, AWS provisioning, secrets, Resend/live sending, cold outreach enablement, Stripe money movement, SMS, or live scraping. See [evidence/phase-3-7e-staging-release-runbook-plan.md](evidence/phase-3-7e-staging-release-runbook-plan.md).

P3-7e-dryrun local staging rehearsal (2026-06-30): production Docker images built, booted, migrated, and smoked locally. `frontend/Dockerfile.prod` ARG/ENV fix for `NEXT_PUBLIC_CLERK_MOCK_MODE` / `NEXT_PUBLIC_API_BASE_URL` was pre-existing in `8634f47` (required to bake `NEXT_PUBLIC_*` vars into the Next.js bundle at build time; default `NEXT_PUBLIC_CLERK_MOCK_MODE=false` keeps production CI secure). This slice is docs-only — evidence + doc updates. Backend gates: Ruff/Black/mypy/731 pytest PASS. Frontend gates: lint/typecheck/141 vitest/build PASS. Backend image `sha256:aa7caf65c7f1e756041c954991b22a9e4820f110d959d1781db128ede1db2474`; frontend image `sha256:97bf44c2a0dfefb6ad3e9a4aa7fa71b78e18258f266d3eb4ba70725da36181cb`. Migration one-off: DB already at head `00022_platform_admin_role`. `/health` 200, `/live` 200, `/ready` 200 (`database: ok`, `migrations: up_to_date`, `rate_limit_backend: in_memory`). Browser smoke: mock login via `test@example.com` / `password` on prod frontend container — form visible, login succeeded, dashboard loaded, session persisted, sign-out worked. Stripe checkout/portal fail-closed (`503 STRIPE_CHECKOUT_NOT_AVAILABLE` / `503 STRIPE_PORTAL_NOT_AVAILABLE`). No secrets in logs. No real send, no real provider, no registry push, no deployment. Honest limits: `APP_ENV=local` (boot guard no-op), no managed Redis, no real Clerk, no RDS, no TLS, no registry push. See [evidence/phase-3-7e-local-staging-rehearsal.md](evidence/phase-3-7e-local-staging-rehearsal.md).

P3-5h-prep internal-only Resend smoke preparation (2026-06-28): docs-only smoke checklist created. Future real smoke remains blocked until the concrete Resend secret refs, DNS verification, monitored Reply-To, legal/company footer details, internal recipient, emergency-stop owner, deliverability owner, real adapter implementation, and explicit owner approval are recorded. Smoke must be one internal email only, with no prospect/client recipient, no automatic follow-up, no open/click tracking, full gate evidence, and a rollback/emergency-stop result. See [evidence/phase-3-5h-prep-internal-resend-smoke.md](evidence/phase-3-5h-prep-internal-resend-smoke.md).

P3-5i Resend secret-readiness contract (2026-06-28): docs-only readiness contract created. Defines secret-ref rules, DNS/domain proof, smoke owner values, gate readiness, `config_ready` / `smoke_ready` / `send_ready` / `production_ready` state definitions, secret-resolution boundary, evidence requirements, and hard stops. No code, Resend SDK/API call, credentials, deployment, live-provider behavior, or production enablement was added. See [evidence/phase-3-5i-resend-secret-readiness-contract.md](evidence/phase-3-5i-resend-secret-readiness-contract.md).

P3-Demo-1 mock send path readiness (2026-06-29): evidence-only verification confirms the local/mock demo can show Phase 0 foundation, tenant/auth/billing/access gates, campaign/contact flow, mock draft/evidence, human review, send-gate dry-run, mock send intent/outbound/audit, deliverability/outcomes read path, suppression/compliance gates, and rate limits. It also confirms cold outreach remains mock-only and cannot route through Resend, Stripe remains fail-closed with no money movement, and no production/deployment/provider enablement occurred. See [evidence/phase-3-demo-1-mock-send-path-readiness.md](evidence/phase-3-demo-1-mock-send-path-readiness.md).

1. Prepare hardened backend/frontend/worker runtime images.
2. Keep production Docker builds in CI/CD before staging release.
3. Use the staging env/secret template to collect owner/operator values.
4. Add release/deploy automation only after owner/operator values and explicit approval.
5. Deploy to **staging first** after owner approval.
3. Run migrations in a one-off task.
4. Run smoke tests.
5. Release backend, worker, frontend.
6. Verify readiness (`/health`, `/live`, `/ready`).
7. Run synthetic campaign in mock mode.
8. Promote to production **only after staging passes** and a separate production cutover is approved.

## B4. Migration & rollback rules

- Prefer **backward-compatible** migrations. No destructive migration without backup + rollback plan.
- Long-running indexes created concurrently where possible; vector indexes only after enough rows + `ANALYZE`.
- Every migration has rollback notes. Keep previous container image tag + ECS task definition.
- **Do not blindly roll back DB after a destructive migration.** Feature flags must allow disabling new features. Failed deployment -> incident record.

## B5. Backup/restore

- RDS automated backups enabled; daily snapshots before production launch.
- **Restore drill before external users.** Document **RPO/RTO**. S3 versioning enabled for uploads/exports.

---

# Part C - Environment safety & go/no-go

## C1. Production/staging boot guard

Backend **and** workers fail boot on unsafe config (mock providers in prod, blank/placeholder secrets, secrets not sourced from AWS Secrets Manager in production, KMS/Secrets Manager unavailable, RLS off/not-forced, `BYPASSRLS` roles, migration/code mismatch, disabled cookie/CORS/CSRF/HTTPS, unverifiable tenant context, missing production Redis rate-limit backend/URL). Full fail-boot condition list + allowed-environments table -> [CLAUDE](../CLAUDE.md).

Redis reachability is not a boot-time network check in P3-4c; it should be added to readiness/smoke checks before production cutover so boot stays deterministic while `/health/ready` can verify dependencies.

## C2. Staging/prod parity

Staging mirrors production config; mock providers in staging only for explicit test suites with live-like checks also running. Synthetic mock-mode campaign runs in the pipeline before promotion.

## C3. Ops go/no-go checks

- [ ] Backup **restore drill** passed (else NO-GO).
- [ ] MVP in-product observability and LangSmith faithfulness logging configured.
- [ ] Boot guard active in backend + workers.
- [ ] Readiness/migration checks green; previous image/task def retained for rollback.

Full launch go/no-go + blockers -> [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md).
