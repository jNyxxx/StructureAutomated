# Workers, Queue & Webhooks

**Purpose:** Job/queue model (Postgres source of truth, SQS production transport), worker runtime + lifecycle, retries/DLQ/idempotency, n8n boundaries, and inbound webhook verification + async processing.
**Source sections:** Master guide §17 (n8n/webhooks/jobs/queue), §8 (worker tenant context).
**Status:** Draft (transport choice → [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md))
**Related docs:** [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`jobs`, `idempotency_keys`, `webhook_events`, `send_intents`) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) (claim-time re-check) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (duplicate-send) · [API_CONTRACT](API_CONTRACT.md) (webhook routes) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) (worker context)

---

## 1. Queue model

- **Postgres `jobs`/outbox table is the durable source of truth.**
- Production dispatch uses **SQS**; local development may poll Postgres.
- **EventBridge** schedules recurring jobs.
- DLQ is represented in job status **and** SQS DLQ in production.

Transport rationale → [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md).

## 2. Worker types

`import_worker`, `agent_worker`, `send_worker`, `followup_worker`, `warmup_worker`. All reuse the **same services/gates as routes** (CLAUDE rule 5).

## 3. Job lifecycle

Every tenant job payload includes: `tenant_id`, `actor_user_id`/`system_actor`, `correlation_id`, `job_id`, `idempotency_key`, `requested_permission`.

1. **Claim job atomically** (lease via `locked_until`).
2. **Fail closed** if tenant context missing for tenant work.
3. Set tenant context through the same helper as HTTP requests.
4. **Re-check subscription, usage, permission, and object access** at claim time ([BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md): a job queued while active must not send if tenant becomes locked).
5. Execute job.
6. Mark success / failure / dead-letter.
7. Emit audit + outcome events.

## 4. Retries, leases, DLQ

| Failure type | Behavior |
|---|---|
| Provider/network errors | Exponential backoff, **max 5 attempts** |
| Validation/permission/billing failures | **Non-retryable fail** |
| Unknown send result | Provider lookup **before** retry |
| Max attempts exceeded | **Dead-letter + alert** |

Leases: claim sets `locked_until`; expired leases are reclaimable.

> **"5 vs 3" — two distinct limits, not a contradiction.** The **max 5 attempts** in the table applies to *provider/network transient errors* (extra exponential-backoff retries against a flaky provider/network). The **general job retry cap is 3** for other retryable job failures — matching the `Max job retries: 3` default in [AI_SAFETY_AND_GROUNDEDNESS §7](AI_SAFETY_AND_GROUNDEDNESS.md) cost controls. Neither changes the rules in the table above.

## 5. Idempotency & no-duplicate guarantees

- Deterministic job keys; jobs/retries must **never** duplicate sends, billing changes, imports, outcomes, or webhook effects (CLAUDE rule 13).
- Send path: row lock before provider call + unique `send_intent_id` + provider idempotency key — enforced in [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) and the DB.

## 6. Logging

Structured JSON logs with `correlation_id`, `job_id`, `tenant_id` on every job. Secrets never logged (CLAUDE rule 14). Full log shape/alerts → [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md).

## 7. n8n boundaries

**n8n may:** trigger scheduled campaign runs · inject mock outcomes for demo · receive provider-like mock callbacks · trigger daily deliverability monitor · send internal Slack/email notifications.

**n8n must not:** bypass backend auth · send messages directly · mark billing active · disable gates · access DB directly · store tenant secrets outside approved storage. (Integration glue only — never an authority for sends, billing, auth, or tenant access.)

## 8. Webhook verification & processing

- **Stripe:** verify `Stripe-Signature` over raw body.
- **n8n internal:** HMAC or shared-secret header, rotatable, **fail closed**.
- **Future Twilio/mailbox:** provider-specific signature verification before parsing.
- Flow: **verify raw-body signature → store first (`webhook_events`) → return 2xx only after durable storage → dedupe by provider event ID → process asynchronously via queue → idempotent → audit.** Failed processing leaves the event retryable (replay-safe).

## 9. Acceptance criteria

- [ ] Worker fails closed without tenant context; cannot process Tenant B job under Tenant A context.
- [ ] Billing re-checked at claim time; locked tenant cannot send.
- [ ] Crash/retry/DLQ tested; no duplicate sends, billing changes, imports, or webhook effects.
- [ ] Webhook signature verified before parse; stored before 2xx; dedupe + async + retryable on failure.
- [ ] n8n cannot bypass auth/gates, send directly, or touch the DB.
