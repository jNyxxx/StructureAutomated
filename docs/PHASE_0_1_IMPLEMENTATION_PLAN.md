# Phase 0 + Phase 1 Implementation Plan

**Purpose:** Practical build sequence and scope for Phase 0 (foundation) and Phase 1 (cold-outreach MVP demo) only — what to build, in what order, what *not* to build yet, and where completion is proven. Checklist, not a rebuild of the guide.
**Source sections:** Master guide §1 (MVP boundary), §24 (roadmap), §26 (start-here).
**Status:** Draft
**Related docs:** [CLAUDE](../CLAUDE.md) (rules) · [ARCHITECTURE](ARCHITECTURE.md) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) · [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (completion gates) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · all domain docs

> Multi-tenant marketing-automation SaaS under a strict tenant boundary. **Only Phase 0 + Phase 1 are in scope** for this build.

---

## 1. Phase 0 — platform foundation (secure substrate)

- [ ] Repo structure + governance docs (this set).
- [ ] Docker local stack ([OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md)).
- [ ] FastAPI backend + Next.js frontend foundation.
- [ ] PostgreSQL 16+ with pgvector, citext, pgcrypto, uuid-ossp; Alembic migrations.
- [ ] **Forced RLS** on tenant tables + tenant-scoped DB helper ([DATABASE_SCHEMA](DATABASE_SCHEMA.md)).
- [ ] Auth/session lifecycle (first-party or managed) — **locked by ADR before coding** ([AUTH_AND_RBAC](AUTH_AND_RBAC.md), [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md)).
- [ ] RBAC + object authorization.
- [ ] Billing/subscription/usage skeleton ([BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md)).
- [ ] Durable jobs/outbox, SQS-ready ([WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md)).
- [ ] Idempotency framework; audit + structured logs; mock/live adapter pattern.
- [ ] CI: lint, migration smoke, RLS isolation, secret scan, Docker smoke.

## 2. Phase 1 — cold-outreach MVP demo (CRE)

- [ ] CRE demo tenant seed data.
- [ ] CSV import: validation, dedupe, suppression checks, import audit ([EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md)).
- [ ] Campaign creation + campaign-prospect assignment.
- [ ] LangGraph cold-outreach flow; research snippets + tenant-scoped RAG ([AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md)).
- [ ] AI draft generation; prompt-injection fence; groundedness gate.
- [ ] Review queue (edit/approve/reject) + **re-grounding after edits**.
- [ ] Server-side send gate; mailbox pool, warm-up state machine, throttle, send windows.
- [ ] Mock send adapter (production-shaped); follow-up scheduler.
- [ ] Mock outcomes: sent, bounced, replied, booked meeting, no response.
- [ ] Deliverability + outcomes/ROI dashboards ([FRONTEND_GUIDE](FRONTEND_GUIDE.md)).
- [ ] E2E demo test + completion report.

## 3. Do not build yet (non-goals until Phase 0+1 report accepted)

Real SMS sending · A2P 10DLC/Twilio production registration · Google/Meta Ads production connectors · Google Business Profile connector · advanced CRM automation · advanced SEO/AI-search rank tracking · real mailbox provider integration beyond adapter contracts + mock · live scraping / paid research unless explicitly approved · automatic live sends from signal events · full multi-plan self-serve pricing UI.

## 4. Order of work (start-here sequence)

1. Repo structure; `CLAUDE.md`; completion template.
2. **Lock ADRs first:** [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) (before auth), [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md) (Postgres jobs + SQS), [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md), [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md).
3. Docker Compose: db, backend, frontend, worker, n8n, optional localstack/redis.
4. Alembic migrations: extensions, tenants, users, memberships, sessions/auth, plans, subscriptions, contacts, prospects, campaigns, jobs, idempotency, audit, compliance profile, suppression baseline.
5. Tenant DB helper + forced RLS; ban raw DB access by lint/test convention.
6. Production/staging boot guards + CI.
7. Auth/session (or managed-auth) → RBAC + object-auth tests → billing/usage gate + mock Stripe.
8. CSV import → campaign/prospect services → job queue + worker loop.
9. Agent run tables + LangSmith mock → RAG snippet services → draft generation + groundedness.
10. Review queue + re-grounding → send gate + mailbox/warm-up/throttle → mock send + outcomes.
11. Frontend pages + dashboards → E2E demo test → Phase 0+1 completion report.

## 5. Completion gates

Phase 0 and Phase 1 are "done" only against the gate checklists in [TESTING_AND_AUDIT §3](TESTING_AND_AUDIT.md). Do not mark a phase complete otherwise.

## 6. Forward roadmap (post-MVP, not in scope)

| Phase | Scope | Done when |
|---|---|---|
| 2 | Lead management | Inbound capture, pipeline, scoring, routing, shared lead table. |
| 3 | Email/SMS campaigns | Opted-in drips, SMS consent/compliance, Twilio. **Legal launch blocker.** |
| 4 | Paid ads | Google/Meta connectors, spend/reporting. |
| 5 | Local SEO/AI search | GBP, listings, reviews, AI-search visibility. |
| 6 | Unified dashboard | All components unified beyond MVP dashboard. |

**Do not start Phase 2 until the Phase 0 + Phase 1 completion report is accepted.**

## 7. Gaps / Needs owner decision

- §26 also names a **mock/live-adapter-pattern ADR** and a **privacy-retention-defaults ADR** not in the current 4-ADR set. **Needs owner decision:** add as separate ADRs, or treat mock/live pattern as covered by [ARCHITECTURE](ARCHITECTURE.md)/[CLAUDE](../CLAUDE.md) and retention defaults by [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md) + [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md). (Doc-set naming: guide's `MASTER_ROADMAP`/`DEPLOYMENT_RUNBOOK`/`OBSERVABILITY_RUNBOOK` are folded into this plan + [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md) per the manifest.)
