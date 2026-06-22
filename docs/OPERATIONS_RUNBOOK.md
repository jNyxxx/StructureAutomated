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

1. Deploy to **staging first**.
2. Run migrations in a one-off task.
3. Run smoke tests.
4. Deploy backend, worker, frontend.
5. Verify readiness (`/health/ready`).
6. Run synthetic campaign in mock mode.
7. Promote to production **only after staging passes**.

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

Backend **and** workers fail boot on unsafe config (mock providers in prod, blank/placeholder secrets, secrets not sourced from AWS Secrets Manager in production, KMS/Secrets Manager unavailable, RLS off/not-forced, `BYPASSRLS` roles, migration/code mismatch, disabled cookie/CORS/CSRF/HTTPS, unverifiable tenant context). Full fail-boot condition list + allowed-environments table -> [CLAUDE](../CLAUDE.md).

## C2. Staging/prod parity

Staging mirrors production config; mock providers in staging only for explicit test suites with live-like checks also running. Synthetic mock-mode campaign runs in the pipeline before promotion.

## C3. Ops go/no-go checks

- [ ] Backup **restore drill** passed (else NO-GO).
- [ ] MVP in-product observability and LangSmith faithfulness logging configured.
- [ ] Boot guard active in backend + workers.
- [ ] Readiness/migration checks green; previous image/task def retained for rollback.

Full launch go/no-go + blockers -> [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md).
