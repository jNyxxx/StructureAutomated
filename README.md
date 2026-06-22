# AutomatedStructure

Multi-tenant, high-ticket marketing-automation SaaS. One revenue engine where contacts, prospects, leads, campaigns, outreach, outcomes, compliance, billing, and AI research context live under a **strict tenant boundary**.

## MVP scope

**Only Phase 0 + Phase 1 are in scope:**
- **Phase 0** — secure SaaS foundation (multi-tenant Postgres + forced RLS, auth/RBAC, billing skeleton, jobs/queue, idempotency, audit, CI).
- **Phase 1** — CRE cold-outreach demo in **mock mode** (CSV import → LangGraph drafting → groundedness → review queue → send gate → mock send/outcomes → dashboards).

Out of scope this cycle: real SMS, ads/GBP connectors, advanced CRM/SEO, live mailbox/scraping, signal-triggered live sends, self-serve pricing UI. See [docs/PHASE_0_1_IMPLEMENTATION_PLAN.md](docs/PHASE_0_1_IMPLEMENTATION_PLAN.md).

## ⚠️ Before writing any code

Read **[CLAUDE.md](CLAUDE.md)** — it holds the non-negotiable engineering rules, security rules, mock-mode rules, and the production boot guard. All implementation must comply. Lock the required **ADRs** before coding the areas they govern.

## Local setup

Docker Compose stack (Postgres+pgvector, backend, frontend, worker, n8n). Steps, CI, and deployment → [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).

## Documentation map

| Area | Doc |
|---|---|
| Repo + agent rules | [CLAUDE.md](CLAUDE.md) |
| Architecture, stack, structure | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Database schema + RLS | [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) |
| API contract | [docs/API_CONTRACT.md](docs/API_CONTRACT.md) |
| Auth & RBAC | [docs/AUTH_AND_RBAC.md](docs/AUTH_AND_RBAC.md) |
| Billing state machine | [docs/BILLING_STATE_MACHINE.md](docs/BILLING_STATE_MACHINE.md) |
| Email compliance & send gate | [docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md](docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md) |
| AI safety & groundedness | [docs/AI_SAFETY_AND_GROUNDEDNESS.md](docs/AI_SAFETY_AND_GROUNDEDNESS.md) |
| Workers, queue & webhooks | [docs/WORKERS_QUEUE_AND_WEBHOOKS.md](docs/WORKERS_QUEUE_AND_WEBHOOKS.md) |
| Privacy & retention | [docs/PRIVACY_AND_RETENTION.md](docs/PRIVACY_AND_RETENTION.md) |
| Frontend guide | [docs/FRONTEND_GUIDE.md](docs/FRONTEND_GUIDE.md) |
| Operations runbook | [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) |
| Testing & audit | [docs/TESTING_AND_AUDIT.md](docs/TESTING_AND_AUDIT.md) |
| Implementation plan | [docs/PHASE_0_1_IMPLEMENTATION_PLAN.md](docs/PHASE_0_1_IMPLEMENTATION_PLAN.md) |
| Launch blockers & owner decisions | [docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md](docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) |
| Decision records | [docs/ADRs/](docs/ADRs/) |
| Doc tracker | [docs/DOCUMENTATION_MANIFEST.md](docs/DOCUMENTATION_MANIFEST.md) |

> Source of truth: `AutomatedStructure_Final_Master_Build_Guide.md`. If a generated doc disagrees with it, the guide wins unless stricter signed legal/provider/incident rules apply.
