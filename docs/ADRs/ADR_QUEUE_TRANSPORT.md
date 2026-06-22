# ADR — Queue Transport

**Status:** Accepted (locked)
**Date:** 2026-06-22

## Context

The platform needs durable, idempotent background processing for imports, agent runs, sends, follow-ups, warm-up, billing, and webhooks. Jobs must survive crashes, never duplicate side effects, and run identically in local and production.

## Decision

- **Postgres `jobs`/outbox table is the durable source of truth.**
- **SQS is the production dispatch transport.**
- **Local development may poll Postgres** directly (no SQS required).
- **EventBridge** schedules recurring jobs.
- DLQ is represented in **job status** and in **SQS DLQ** in production.

## Options considered

| Option | Verdict |
|---|---|
| Postgres-only (poll in all envs) | Fine locally; insufficient dispatch scaling for production |
| SQS-only (queue is source of truth) | Loses durable, queryable, tenant-scoped job state in the DB |
| **Postgres source of truth + SQS dispatch** | **Chosen** — durable/queryable state in DB, scalable dispatch in prod, simple local polling |

## Consequences

- **Retry defaults:** provider/network errors → exponential backoff, max 5 attempts; validation/permission/billing failures → non-retryable fail; unknown send result → provider lookup **before** retry; dead-letter after max attempts **with alert**.
- **Idempotency:** deterministic job keys; jobs/retries must never duplicate sends, billing changes, imports, outcomes, or webhook effects (CLAUDE rule 13).
- Workers claim atomically (lease via `locked_until`), set tenant context, and re-check billing/permissions at claim time.
- Webhooks are stored first, deduped, then processed asynchronously through the queue.

## Owner decisions / open questions

- [ ] SQS standard vs FIFO per queue family — **implementation detail to confirm** (not specified in the guide; choose per ordering/dedup needs).

## Related docs

[WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) · [DATABASE_SCHEMA](../DATABASE_SCHEMA.md) (`jobs`, `idempotency_keys`) · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md) (queue alerts)
