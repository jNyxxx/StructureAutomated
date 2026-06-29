# Architecture

**Purpose:** System architecture, tenant boundary, **canonical** locked stack, layer responsibilities, trust boundaries, mock-vs-production model, and project structure. This is the single source for the locked stack — other docs reference here, never restate it.
**Source sections:** Master guide §4 (locked stack), §5 (high-level architecture + trust boundaries), §10 (backend structure + layer rules), §18 (App Router structure).
**Status:** Draft
**Related docs:** [CLAUDE](../CLAUDE.md) (rules + env guard) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) · [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md) · [AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md)

---

## 1. Product architecture (request → durable state)

```text
Client Browser — Next.js App Router UI
  Holds NO final permissions, billing truth, quota authority, or send authority
        |
        v
FastAPI Backend
  Auth/session middleware → Tenant resolver → RBAC + object authz
  → Billing/usage gate → Rate limiting → Validation + standard error envelope
  → Service layer → tenant-scoped repository layer
        |
        +--> PostgreSQL 16 + pgvector   (forced RLS, constraints, audit, idempotency, durable state)
        +--> Jobs/Outbox                (source of truth; SQS dispatch in production)
        +--> Verified Webhook Intake    (raw-body signature verify, dedupe, async)

Workers: import_worker, agent_worker, send_worker, followup_worker, warmup_worker
  Must set tenant context, re-check billing/permissions, enforce idempotency
        |
        v
LangGraph Agents
  research -> enrich -> RAG -> draft -> fence -> groundedness -> review -> send gate -> schedule
        |
        v
Tool/Connector Layer — registered tools only, tenant-scoped, permissioned, validated, audited
        |
        v
External Providers - future Stripe, mailbox, DNS, verifier, research, future Twilio/GBP/ads
  Mocked in MVP through production-shaped adapters
```

---

## 2. Locked technology stack (canonical)

| Layer | Locked choice |
|---|---|
| Frontend | Next.js App Router, TypeScript, Tailwind, shadcn/ui, Zod, Recharts |
| Backend | FastAPI, Python 3.12+, Pydantic, asyncpg, SQLAlchemy/Alembic for migrations |
| Database | PostgreSQL 16+, pgvector, uuid-ossp, citext, pgcrypto, forced RLS |
| AI/agents | LangGraph, LangSmith tracing/evals, OpenAI-compatible provider abstraction, deterministic mock provider |
| Workers/queue | PostgreSQL jobs/outbox as source of truth; SQS for production dispatch; local worker may poll Postgres |
| Automation | n8n only for orchestration/webhook glue — never core business or security rules |
| Billing | Mock-only local MVP gates; real Stripe deferred until first-paying-client production billing |
| Infra | Docker Compose local; AWS ECS/Fargate, RDS PostgreSQL, SQS, EventBridge, AWS Secrets Manager, AWS KMS, S3, CloudWatch, ALB, WAF |
| Observability | Structured JSON logs, correlation IDs, CloudWatch alarms, LangSmith, Sentry or equivalent |

> Queue transport (SQS vs Postgres outbox) rationale is recorded in [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md).

---

## 3. Layer responsibilities

| Layer | Responsibility |
|---|---|
| Routers | Validate request/response; call services only. |
| Services | Enforce permissions, billing, idempotency, business rules. |
| Repositories | Tenant-scoped SQL only. |
| Agents/tools | No direct DB access; never send directly. |
| Workers | Reuse the same services/gates as routes; set tenant context; enforce idempotency. |
| n8n | Calls backend APIs or verified webhooks only. |

Enforcement framing and hard stops: see [CLAUDE](../CLAUDE.md).

---

## 4. Tenant boundary & trust boundaries

- **Tenant boundary:** every tenant-owned table carries `tenant_id` with forced RLS; HTTP requests and worker jobs set DB tenant context before any query. Detailed isolation + support-access model: [AUTH_AND_RBAC](AUTH_AND_RBAC.md).
- Browser, CSV uploads, webhooks, research snippets, AI outputs, tool outputs, and n8n payloads are **untrusted until validated**.
- **n8n** is integration glue, not an authority for sends, billing, auth, or tenant access.
- **Workers** are trusted only when using the same tenant/auth/billing/permission/idempotency libraries as the API.
- **Database RLS is the final guardrail, not the only guardrail** — permission + object-ownership checks still required (CLAUDE rule 6).

---

## 5. Dual Sending-Layer Architecture

Email sending is split into two independent layers with separate providers, subdomains,
and routing guards:

| Layer | Provider | Subdomain | Status |
|---|---|---|---|
| Transactional / opted-in | Resend | `outreach.automatedstructure.com` | Skeleton; live disabled |
| Cold outreach | Mailbox-pool manager | Dedicated cold-sending subdomains (not acquired) | Future; mocked for MVP |

`ProviderSendRequest.send_layer` distinguishes the two layers at the adapter boundary.
Default is `"cold_outreach"` (fail-closed). `ResendEmailSendProvider` rejects
`send_layer == "cold_outreach"` with code `COLD_OUTREACH_NOT_ALLOWED` (422) before
any live-send check. Cold outreach must NEVER route through Resend or any
transactional/bulk ESP.

---

## 6. Mock vs production model

Providers are mocked **through production-shaped adapters** — architecture, interfaces, audit, gates, idempotency, and tenant isolation stay real in every mode.

| | Mocked in MVP | Never mocked (always real) |
|---|---|---|
| Components | External email delivery · mailbox warm-up clock · email verification · DNS/domain auth · public research results (when no live tool) · mock billing transitions · n8n external callbacks · reply/bounce/booked outcome events | Tenant isolation + forced RLS · auth/authz · billing/feature/usage enforcement · idempotency · queue state transitions · send gate · groundedness verdict storage · human approval · audit logs · outcome event emission · rate limits |

Enforcement rules (rule 11) and the production boot guard live in [CLAUDE](../CLAUDE.md).

---

## 7. Project structure

**Backend** (`backend/app/`):

```text
main.py · config.py · database.py
middleware/ · routers/ · schemas/ · services/ · repositories/ · models/
workers/ · agents/ · tools/ · integrations/ · audit/ · observability/
```

**Frontend** (`frontend/app/`, App Router):

```text
(auth)/login · (auth)/signup · (auth)/verify-email
(app)/dashboard · (app)/prospects · (app)/prospects/import
(app)/campaigns · (app)/campaigns/[id] · (app)/campaigns/[id]/drafts
(app)/review-queue · (app)/deliverability · (app)/outcomes
(app)/settings · (app)/settings/team · (app)/settings/integrations
(app)/billing · (app)/audit-logs
```

Frontend rules, required MVP pages, review-diff view, and accessibility: [FRONTEND_GUIDE](FRONTEND_GUIDE.md).
