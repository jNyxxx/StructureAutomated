# Phase 0 + Phase 1 Implementation Plan

**Purpose:** Practical build sequence and scope for Phase 0 (foundation) and Phase 1 (cold-outreach MVP demo) only - what to build, in what order, what *not* to build yet, and where completion is proven. Checklist, not a rebuild of the guide.
**Source sections:** Master guide §1 (MVP boundary), §24 (roadmap), §26 (start-here).
**Status:** Draft
**Related docs:** [CLAUDE](../CLAUDE.md) (rules) - [ARCHITECTURE](ARCHITECTURE.md) - [DATABASE_SCHEMA](DATABASE_SCHEMA.md) - [AUTH_AND_RBAC](AUTH_AND_RBAC.md) - [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (completion gates) - [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) - all domain docs

> Multi-tenant marketing-automation SaaS under a strict tenant boundary. **Only Phase 0 + Phase 1 are in scope** for this build.

---

## 1. Phase 0 - platform foundation (secure substrate)

- [ ] Repo structure + governance docs (this set).
- [ ] Docker local stack ([OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md)).
- [ ] FastAPI backend + Next.js frontend foundation.
- [ ] PostgreSQL 16+ with pgvector, citext, pgcrypto, uuid-ossp; Alembic migrations.
- [ ] **Forced RLS** on tenant tables + tenant-scoped DB helper ([DATABASE_SCHEMA](DATABASE_SCHEMA.md)).
- [ ] Clerk-managed auth integration; app-owned tenant membership, RBAC, object authorization, billing gates, support access, audit, tenant context, and RLS.
- [ ] Platform-admin MFA required before external users / production.
- [ ] RBAC + object authorization.
- [ ] Mock-only billing foundation: billing schema, tenant subscription/plan relationship, `tenant_status`, centralized access gates, mock transitions, deterministic tests.
- [ ] Durable jobs/outbox, SQS-ready ([WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md)).
- [ ] Idempotency framework; audit + structured logs; mock/live adapter pattern.
- [ ] AWS Secrets Manager + AWS KMS secret-handling interface for production; local/mock backend may use the same interface.
- [ ] Production boot guard for unsafe config, placeholder secrets, missing approved secret backend, RLS, tenant context, and mock providers.
- [ ] CI: lint, migration smoke, RLS isolation, secret scan, Docker smoke.

## 2. Phase 1 - cold-outreach MVP demo (CRE)

- [ ] US-first compliance assumptions for cold email; SMS remains post-MVP.
- [ ] CRE demo tenant seed data.
- [ ] CSV import: validation, dedupe, suppression checks, import audit ([EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md)).
- [ ] Campaign creation + campaign-prospect assignment.
- [ ] LangGraph cold-outreach flow; research snippets + tenant-scoped RAG ([AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md)).
- [ ] AI draft generation; prompt-injection fence; groundedness gate.
- [ ] Review queue (edit/approve/reject) + **re-grounding after edits**.
- [ ] First real client policy: every AI-generated cold-email draft requires manual human approval, even after all safety gates pass.
- [ ] Server-side send gate; mailbox pool, warm-up state machine, throttle, send windows.
- [ ] Mock send adapter (production-shaped); follow-up scheduler.
- [ ] Mock outcomes: sent, bounced, replied, booked meeting, no response.
- [ ] Deliverability + outcomes/ROI dashboards ([FRONTEND_GUIDE](FRONTEND_GUIDE.md)).
- [ ] In-product observability and LangSmith faithfulness logging for the demo.
- [ ] E2E demo test + completion report.

## 3. Do not build yet

Real SMS sending - A2P 10DLC/Twilio production registration - real Stripe checkout - real Stripe calls - real Stripe webhooks - dunning/money movement - Google/Meta Ads production connectors - paid ad spend - Google Business Profile connector - advanced CRM automation - advanced SEO/AI-search rank tracking - real mailbox provider integration beyond adapter contracts + mock - live scraping / paid research unless explicitly approved - automatic live sends from signal events - auto-send for first real client - Slack/internal alerts - full multi-plan self-serve pricing UI.

## 4. Order of work (start-here sequence)

1. Repo structure; `CLAUDE.md`; completion template.
2. Confirm ADRs already locked: [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) (Clerk), [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md) (Postgres jobs + SQS), [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md) (mock-only MVP billing), [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) (US baseline).
3. Docker Compose: db, backend, frontend, worker, n8n, optional localstack/redis.
4. Alembic migrations: extensions, tenants, users with Clerk identity mapping, memberships, minimal app auth-session/revocation records, plans, subscriptions, contacts, prospects, campaigns, jobs, idempotency, audit, compliance profile, suppression baseline.
5. Tenant DB helper + forced RLS; ban raw DB access by lint/test convention.
6. Production/staging boot guards + CI.
7. Clerk auth integration -> RBAC + object-auth tests -> mock billing gates.
8. CSV import -> campaign/prospect services -> job queue + worker loop.
9. Agent run tables + LangSmith mock -> RAG snippet services -> draft generation + groundedness.
10. Review queue + re-grounding -> send gate + mailbox/warm-up/throttle -> mock send + outcomes.
11. Frontend pages + dashboards -> E2E demo test -> Phase 0+1 completion report.

## 5. Completion gates

Phase 0 and Phase 1 are "done" only against the gate checklists in [TESTING_AND_AUDIT §3](TESTING_AND_AUDIT.md). Do not mark a phase complete otherwise.

## 6. Forward roadmap (post-MVP, not in scope)

| Phase | Scope | Done when |
|---|---|---|
| First paying client / production billing | Real Stripe checkout, webhooks, dunning, reconciliation, plan entitlements, money movement | Local mock cold-outreach demo works and owner approves onboarding the first paying client. |
| 2 | Lead management | Inbound capture, pipeline, scoring, routing, shared lead table. |
| 3 | Email/SMS campaigns | Opted-in drips, SMS consent/compliance, Twilio. **Legal launch blocker.** |
| 4 | Paid ads | Google/Meta connectors, spend/reporting. |
| 5 | Local SEO/AI search | GBP, listings, reviews, AI-search visibility. |
| 6 | Unified dashboard | All components unified beyond MVP dashboard. |

**Do not start Phase 2 until the Phase 0 + Phase 1 completion report is accepted.**

## 7. Remaining decisions

- Counsel-approved legal/privacy/terms/outreach/unsubscribe/data-use language before live sending.
- Approved live research/scraping/paid-provider sources before live research.
- Production mock-provider exception only if a named controlled production demo is later requested.
- First-paying-client production billing details such as Stripe products/prices and plan entitlements.
- Keep the 20-doc set locked; do not add duplicate ADRs/docs unless a future owner decision changes doc governance.
