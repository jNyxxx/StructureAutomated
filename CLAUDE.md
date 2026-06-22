# CLAUDE.md

**Purpose:** Non-negotiable repo rules, architecture constraints, security rules, and hard stops for all developers and AI coding agents. Read before writing any code.
**Source sections:** Master guide §2 (canonical rules, env guard), §6 (mock mode), §10 (layer rules, credential encryption), §27 (preservation checklist).
**Status:** Draft
**Related docs:** [ARCHITECTURE](docs/ARCHITECTURE.md) (stack, layers, mock map) · [DATABASE_SCHEMA](docs/DATABASE_SCHEMA.md) (RLS) · [AUTH_AND_RBAC](docs/AUTH_AND_RBAC.md) · [API_CONTRACT](docs/API_CONTRACT.md) · [DOCUMENTATION_MANIFEST](docs/DOCUMENTATION_MANIFEST.md)

---

## Source-of-truth order

1. This master build guide.
2. Generated repo docs (`docs/` + ADRs).
3. Previous audit-hardened master guide.
4. Pre-production audit report (historical risk register).
5. Original engineering brief (strategic product intent).

If this guide conflicts with **signed legal policy, provider terms, or production-incident decisions**, the stricter legal/operational rule wins **and an ADR must record the change**.

---

## Non-negotiable engineering rules

1. Every tenant-owned table has `tenant_id`, RLS enabled, and RLS **forced**.
2. No application role used by API/workers may have `BYPASSRLS`.
3. Every tenant data request sets DB tenant context **before** queries.
4. Every worker job touching tenant data sets tenant context **before** queries.
5. Routers, services, agents, tools, and n8n handlers must not use raw DB connections — **tenant-scoped helpers only**.
6. RLS is required but not enough. Every route needs **permission checks and object-ownership checks**.
7. Risky actions require **idempotency**: imports, campaign runs, draft generation, approvals, scheduling, sends, webhooks, billing, exports, deletion.
8. Billing and quota gates run in **routes, services, workers, and scheduled jobs**.
9. Human approval **cannot bypass** prompt-injection checks, groundedness, suppression, billing, throttles, deliverability, or send gates.
10. Agent tools require tenant scope, action permission, allowlist, rate limit, output validation, and audit logs.
11. Mock mode must use the **same** interfaces, schemas, error shapes, rate-limit behavior, and audit records as live mode.
12. Provider webhooks must **verify raw-body signatures before parsing**.
13. Jobs and retries must **never duplicate** sends, billing changes, imports, outcomes, or webhook effects.
14. Secrets never enter Git, logs, prompts, audit details, exports, frontend bundles, or client responses.
15. Completion requires tests, traces, logs, docs, and a completion report — not just code.

---

## Hard stops (coding-agent constraints)

- **Docs-only phases:** do not modify backend/frontend code, DB migrations, tests, package/config/Docker/app files, or the master guide without explicit approval.
- Never weaken RLS, tenant context, or any gate to make something pass.
- No raw DB connections anywhere (rule 5). Agents/tools never touch the DB directly and never send directly.
- Never bypass a safety gate via human approval (rule 9).
- Never place secrets where rule 14 forbids.
- Missing/ambiguous/conflicting requirement → mark **"Needs owner decision"**, do not guess or invent.

---

## Security rules

- **Credential encryption (§10):** prod secrets in AWS Secrets Manager; tenant credentials envelope-encrypted with KMS or stored as secret references. Postgres stores only `secret_ref`, encrypted metadata, version, rotation timestamps. Decrypt only inside integration services. Decrypted values must never reach logs, prompts, audits, tool outputs, exports, or frontend responses.
- **Webhooks:** verify raw-body signature before parsing (rule 12), then dedupe.
- **Rate limits:** required on auth, refresh, imports, agent/tool calls, sends, webhooks, billing — see [API_CONTRACT](docs/API_CONTRACT.md).

---

## Layer rules (enforcement)

Responsibilities are described in [ARCHITECTURE](docs/ARCHITECTURE.md). Hard boundaries:

- Routers validate request/response and call **services only**.
- Services enforce permissions, billing, idempotency, and business rules.
- Repositories do **tenant-scoped SQL only**.
- Agents/tools: **no direct DB access, never send**.
- Workers reuse the **same services/gates** as routes.
- n8n calls backend APIs or **verified webhooks only** — never an authority for sends, billing, auth, or tenant access.

---

## Mock-mode rules

- Mock mode is for local dev, tests, and controlled demos — **never** production readiness.
- Mock mode uses the **same** interfaces/schemas/error-shapes/rate-limits/audit as live (rule 11). Providers are mocked through production-shaped adapters.
- **Never mocked (must stay real):** tenant isolation + forced RLS, auth/authz, billing/feature/usage enforcement, idempotency, queue state transitions, send gate, groundedness storage, human approval, audit logs, outcome events, rate limits.
- Full mocked-vs-real component map: see [ARCHITECTURE](docs/ARCHITECTURE.md).

---

## Production/staging environment safety guard

Add a startup guard in **backend and workers**. Do not rely on developer memory. `APP_ENV=production` must **fail boot** if any are true:

- Mock Stripe / mailbox / DNS / verifier / research providers enabled outside an explicitly named demo environment.
- Required webhook secrets are blank, placeholder, or not from the approved secrets backend.
- Placeholder API keys, encryption keys, JWT secrets, or DB credentials present.
- RLS is disabled, not forced, or missing on any tenant-owned table.
- API or worker DB roles have `BYPASSRLS`.
- App cannot verify DB tenant-context setup at startup.
- Required migration version ≠ deployed code.
- Required cookie/CORS/CSRF/HTTPS security settings disabled.

| Environment | Mock providers? | Rule |
|---|---|---|
| `local` / `development` | Yes | Allowed for local tests and demos. |
| `staging` | Limited | Only for explicit test suites; live-like checks must also run. |
| `demo` | Limited | Only when clearly labeled demo with no real client data. |
| `production` | No by default | Live providers + real secrets required, unless owner-approved controlled-demo exception is recorded. |

---

## Critical areas that must never be silently dropped (§27)

Phase 0/1 scope + do-not-build list · multi-tenancy/forced RLS/tenant helpers/support access · auth & session lifecycle (rotation, reuse detection, revocation, MFA position) · RBAC + object auth · billing states/gates/Stripe · idempotency · queue/outbox/n8n boundaries · API contract + error envelope · CSV import/validation · agent flow/tool registry/prompt-injection/groundedness/re-grounding/human review · send gate/no-send codes/suppression/duplicate-send/deliverability · RAG/embedding governance · privacy/retention/export/delete/vector purge · credential encryption · observability/alerts · CI/CD/migration/rollback/backup · test suites/phase gates/evidence bundle/boot guard/go-no-go. Each area's detail lives in its dedicated doc (see [DOCUMENTATION_MANIFEST](docs/DOCUMENTATION_MANIFEST.md)).
