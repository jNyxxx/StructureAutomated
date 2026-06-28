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
- P3-5e owner approval (2026-06-28): **Resend** selected as the pilot email provider; sending subdomain `outreach.automatedstructure.com`; conservative first-pilot caps (tenant 10/hr·50/day, campaign 50/day, mailbox 25/day); webhook events normalized to `delivered`/`bounced`/`complained`/`deferred`/`failed`/`unsubscribed` with signature verify + idempotency required (no open/click tracking). Real sending stays disabled (`EMAIL_PROVIDER=mock`, `LIVE_EMAIL_SENDING_ENABLED=false`); the Resend adapter is **not** built. **Emergency stop:** owner/operator and engineering can flip `LIVE_EMAIL_SENDING_ENABLED=false` to disable live sending immediately. See [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) §2 and [evidence/phase-3-5e-owner-approval-resend-roadmap.md](evidence/phase-3-5e-owner-approval-resend-roadmap.md).
- Production provider cutover must verify sending domain DNS, webhook signatures, tenant/campaign/mailbox/provider caps, legal footer/unsubscribe copy, and internal-only smoke evidence before any external recipient delivery.

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

P3-7d CI/CD release pipeline plan (2026-06-28): docs-only release plan created. Current CI already covers backend Ruff/Black/mypy/pytest/migration smoke, frontend lint/typecheck/test/build, gitleaks, and pre-commit. Future implementation should add `npm ci`, production Docker image builds, immutable SHA tags, registry push only after approval, migration one-off tasks, staging/production GitHub Environment approvals, smoke evidence capture, and rollback gates. No workflow implementation yet. See [evidence/phase-3-7d-cicd-release-pipeline-plan.md](evidence/phase-3-7d-cicd-release-pipeline-plan.md).

P3-7d-impl CI validation gates (2026-06-28): validation-only workflow hardening implemented. CI now uses `npm ci`, keeps backend/frontend/secret-scan/pre-commit checks, adds changed-file safety guards, and builds backend/frontend production Docker images locally with commit-SHA validation tags only. No release job, registry upload, AWS configuration, staging release, production release, live-provider behavior, or money/SMS/scraping enablement was added. See [evidence/phase-3-7d-ci-validation-gates-implementation.md](evidence/phase-3-7d-ci-validation-gates-implementation.md).

P3-5h-prep internal-only Resend smoke preparation (2026-06-28): docs-only smoke checklist created. Future real smoke remains blocked until the concrete Resend secret refs, DNS verification, monitored Reply-To, legal/company footer details, internal recipient, emergency-stop owner, deliverability owner, real adapter implementation, and explicit owner approval are recorded. Smoke must be one internal email only, with no prospect/client recipient, no automatic follow-up, no open/click tracking, full gate evidence, and a rollback/emergency-stop result. See [evidence/phase-3-5h-prep-internal-resend-smoke.md](evidence/phase-3-5h-prep-internal-resend-smoke.md).

P3-5i Resend secret-readiness contract (2026-06-28): docs-only readiness contract created. Defines secret-ref rules, DNS/domain proof, smoke owner values, gate readiness, `config_ready` / `smoke_ready` / `send_ready` / `production_ready` state definitions, secret-resolution boundary, evidence requirements, and hard stops. No code, Resend SDK/API call, credentials, deployment, live-provider behavior, or production enablement was added. See [evidence/phase-3-5i-resend-secret-readiness-contract.md](evidence/phase-3-5i-resend-secret-readiness-contract.md).

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
