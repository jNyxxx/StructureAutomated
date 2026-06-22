# Phase 0 Implementation Plan — Secure SaaS Foundation (Revised)

> **Planning artifact.** This is the accepted Phase 0 plan. Implementation proceeds slice-by-slice with a checkpoint after each slice. Each slice describes *what* to build, *what migration is needed*, *what tests prove it*, *acceptance criteria*, and *rollback/safety*.

**Goal:** Stand up a secure multi-tenant SaaS foundation (FastAPI + Next.js + PostgreSQL 16) — forced RLS, tenant-scoped DB access, RBAC + object authorization, billing access-gate skeleton, queue/outbox + idempotency, audit logging, **credential encryption / secret handling**, **rate-limit foundation**, mock-adapter registry, production boot guard, CI test gates — before any Phase 1 outreach features.

**Architecture:** Strict layering — routers validate and call **services only**; services enforce permissions/billing/idempotency/rate limits; repositories do **tenant-scoped SQL only**; agents/tools never touch the DB and never send; workers reuse the same services/gates as routes. Every tenant request and worker job sets `SET LOCAL app.current_tenant_id` before any query. RLS is the final guardrail, never the only one.

**Tech Stack (locked — ARCHITECTURE.md:43–56):** Next.js App Router + TS + Tailwind + shadcn/ui + Zod; FastAPI + Python 3.12+ + Pydantic + asyncpg + SQLAlchemy/Alembic; PostgreSQL 16+ with `uuid-ossp`, `vector`, `pgcrypto`, `citext`, forced RLS; Postgres jobs/outbox source of truth + SQS production transport; Clerk auth; mock-only MVP billing gates with real Stripe deferred.

---

## Context

The documentation phase (DOC-1 → DOC-5) is complete and accepted; the 20-doc set is the locked spec. **Repo state confirmed greenfield** (read-only check 2026-06-22: no `.py/.ts/.tsx/.js` files, no `backend/`/`frontend/`/`migrations/`/`alembic/`, no `docker-compose`/`Dockerfile`/`pyproject.toml`/`package.json`/`alembic.ini`; only `docs/`, `CLAUDE.md`, `README.md`, `.gitignore`). Therefore the scaffolding sequence is correct — there is nothing to audit/adapt, only to create.

Phase 0 is infrastructure + safety scaffolding only. No cold-outreach features (campaign import, AI drafting, send gate, mailbox pool, warm-up, deliverability) — those are Phase 1+ and must not start until the Phase 0 + Phase 1 completion report is accepted.

### ADR status (clarified)

| ADR | Status for Phase 0 planning | Effect |
|---|---|---|
| **Auth provider** | **LOCKED = Clerk managed auth.** | Auth slice proceeds (Slice 14). |
| **Queue transport** | **LOCKED = Postgres jobs/outbox source of truth + SQS production transport** (local dev polls Postgres). | Queue slice proceeds (Slice 13). |
| **Billing access-state model** | **LOCKED = mock-only MVP billing** with states `trialing`, `active`, `past_due`, `canceled`, `unpaid`, `inactive`; real Stripe deferred. | Billing slice proceeds (Slice 16) with schema, tenant status, central gates, mock transitions, deterministic tests only. |
| **Compliance jurisdiction** | **LOCKED = United States MVP baseline; first target market = US.** | Compliance/suppression schema proceeds (Slice 17); live sending remains gated by compliance review and owner approval. |

---

## Global Constraints (apply to every slice — CLAUDE.md)

- Every tenant-owned table: `tenant_id UUID NOT NULL`, RLS **enabled and FORCED**; never `client_id`/`workspace_id`/`account_id`.
- **No `BYPASSRLS`** on any app/worker DB role. **No raw DB connections** — tenant helper / repositories only.
- Tenant context (`SET LOCAL app.current_tenant_id`) set before any query, on every request **and** worker job; workers **fail closed** without it.
- Every protected action: authenticated session → active membership → role/action permission → **object ownership (anti-IDOR)** → billing/feature/usage → audit. RLS last, not only.
- Idempotency on risky actions; billing/quota + rate-limit gates in routes, services, workers, scheduled jobs.
- Human approval cannot bypass safety gates. Webhooks: verify raw-body signature **before parsing**, then dedupe.
- **Secrets never** enter Git, logs, prompts, audit details, exports, frontend bundles, or client responses. Mock mode uses the **same** interfaces/schemas/error-shapes/rate-limits/audit as live, via production-shaped adapters.
- Standard error envelope: `{"error":{"code","message","details","request_id"}}`. Never leak cross-tenant existence — generic 404/403 per policy.
- Never weaken RLS, tenant context, auth, billing gates, audit immutability, idempotency, rate limits, or secret handling to make something pass.

---

## 1. Phase 0 implementation sequence (high level)

ADR-independent infrastructure first; the few owner-gated items are isolated. Order reflects hard dependencies.

| # | Slice | Gate | Depends on |
|---|---|---|---|
| 0 | ADR confirmation (governance, no code) | — | docs |
| 1 | Repo scaffolding, tooling, CI skeleton | — | 0 |
| 2 | Docker local stack | — | 1 |
| 3 | Backend foundation: config, logging, request IDs, error envelope, health | — | 1 |
| 4 | Frontend foundation: Next.js skeleton + API client | — | 1 |
| 5 | Alembic + DB connection + extensions migration | — | 3 |
| 6 | DB roles (no BYPASSRLS) + tenant helper + forced-RLS convention + raw-DB ban | — | 5 |
| 7 | Core tenancy schema + identity mapping + forced RLS | — | 6 |
| 8 | Audit logging (append-only) | — | 7 |
| 9 | Mock/live adapter registry + production boot guard | — | 7, 8 |
| 10 | **Credential encryption & secret handling** | — | 9 |
| 11 | Idempotency foundation | — | 7 |
| 12 | **Rate-limit foundation** | — | 3, 11 |
| 13 | Queue/outbox foundation + worker loop | queue LOCKED | 7, 8, 11 |
| 14 | Auth & session (managed auth) + app-side mapping/revocation | auth LOCKED=managed | 7, 8, 12 |
| 15 | RBAC + object-authorization + support-access grants | — | 14 |
| 16 | Mock billing state/access-gate skeleton | billing mock-only LOCKED | 9, 10, 12, 13, 15 |
| 17 | Compliance profile + suppression baseline (schema only) | schema OK; jurisdiction values gated | 7 |
| 18 | Frontend wiring: managed-auth login, tenant context, billing banner, audit view | — | 14, 15, 16 |
| 19 | Phase 0 test-gate suite + E2E smoke + evidence bundle + completion report | all | all |

**Critical path:** 1 → 2 → 5 → 6 → 7 → {8, 11} → 9 → 10 → 13/14 → 15 → 16 → 19. Slices 3/4 parallelize after 1; 12 after 11; 17 after 7.

---

## 2. Implementation slices

Every slice ends with an independently testable, reviewable deliverable. "Migration needed" describes what to author at execution time. Migration numbers are indicative.

---

### Slice 0 — ADR confirmation (governance, no code)
**Objective:** Record ADR sign-offs per the status table: auth = Clerk, queue = Postgres+SQS, billing = mock-only MVP, compliance jurisdiction = United States MVP baseline.
**Files:** `docs/ADRs/*` (status), `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` (mark resolved/gated). *No code.*
**Migration:** None. **Tests:** None (governance).
**Acceptance:** Each ADR status reads Accepted/Locked or explicitly gated, with date + owner.
**Rollback/safety:** Pure docs; git-reversible.

---

### Slice 1 — Repo scaffolding, tooling, CI skeleton
**Objective:** Monorepo layout + tooling (lint, type-check, format, secret scan) + CI pipeline so every later slice lands consistently and safely from day one.
**Files (create):** `backend/app/{middleware,routers,schemas,services,repositories,models,workers,agents,tools,integrations,audit,observability}/` + `main.py`/`config.py`/`database.py` placeholders (ARCHITECTURE.md:100–106); `backend/pyproject.toml` (ruff/mypy/black/pytest); `backend/tests/`; `frontend/` Next.js workspace; `.github/workflows/ci.yml` (jobs grow per slice); `.pre-commit-config.yaml`; extend `.gitignore`; `.env.example` (no real secrets); `docs/templates/COMPLETION_REPORT.md`.
**Migration:** None.
**Tests:** CI runs ruff/`black --check`/mypy clean; secret-scan green; placeholder pytest green.
**Acceptance:** CI runs on PR, all checks green; layout matches ARCHITECTURE.md.
**Rollback/safety:** No runtime/DB/secrets. Fully reversible.

---

### Slice 2 — Docker local stack
**Objective:** One-command local stack identical for all devs + CI smoke.
**Files (create):** `docker-compose.yml` (`db`=PG16, `backend`, `frontend`, `worker`, `n8n`; optional `localstack`, `redis`), `backend/Dockerfile`, `frontend/Dockerfile`, `docker/` init, `.env.example` entries (`APP_ENV=local`, DSN, mock-provider flags).
**Migration:** None (extensions installed by Slice 5 migration, keeping boot-guard migration-version check authoritative).
**Tests:** `docker compose up` → all healthy; CI Docker smoke hits `/health` + Next.js root (200).
**Acceptance:** Stack starts clean from empty volumes; backend reaches `db`.
**Rollback/safety:** Local only; `APP_ENV=local` permits mocks. No real secrets in compose (git-ignored env files).

---

### Slice 3 — Backend foundation: config, structured logging, request IDs, error envelope, health
**Objective:** FastAPI spine — env-aware config, JSON logging with request/correlation IDs, standard error envelope, health/ready/live.
**Files (create):** `backend/app/main.py`, `config.py` (parse `APP_ENV`, DSN, provider flags, security toggles), `middleware/{request_id,logging,error_handler}.py`, `observability/logging.py`, `routers/health.py`, `schemas/errors.py`.
**Migration:** None.
**Error envelope (API_CONTRACT.md — verbatim):** `{ "error": { "code": "PERMISSION_DENIED", "message": "...", "details": {}, "request_id": "req_..." } }`
**Log shape (must include):** `timestamp, level, service, environment, request_id, correlation_id, tenant_id?, actor_id?, job_id?, event, message, metadata`. **Never log** secrets, tokens, credentials, passwords, PII, card numbers, embedding vectors, raw prompts/responses.
**Health:** `/health` (up), `/ready` (DB + migration head — wired Slice 5), `/live`.
**Tests:** error handler emits exact envelope w/ `request_id`; request_id generated/echoed; correlation_id propagates; **redaction test** (no secret/PII leaks); `/health` 200.
**Acceptance:** All exceptions render envelope; every log line carries `request_id`.
**Rollback/safety:** No DB writes. Redaction test guards rule 14.

---

### Slice 4 — Frontend foundation: Next.js skeleton + API client
**Objective:** App Router skeleton + design base + typed API client that understands the error envelope. Foundation only.
**Files (create):** `frontend/app/layout.tsx`; route-group shells `(auth)/{login,signup,verify-email}/`, `(app)/{dashboard,settings,settings/team,settings/integrations,billing,audit-logs}/` (ARCHITECTURE.md:108–119); `frontend/lib/api-client.ts` (parses envelope, surfaces `request_id`); `frontend/lib/zod-schemas.ts`; Tailwind + shadcn config.
**Migration:** None.
**Tests:** API client maps envelope → typed errors; root layout render smoke; lint/type green.
**Acceptance:** App builds + renders shells; envelope errors handled. Frontend role checks are UX-only.
**Rollback/safety:** No secrets in bundle; no auth logic yet (Slice 18).

---

### Slice 5 — Alembic + DB connection + extensions migration
**Objective:** Async DB layer + Alembic + first migration (extensions); wire `/ready` to migration head.
**Files (create):** `backend/app/database.py` (asyncpg pool; connect as **app role**, never superuser), `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_extensions.py`.
**Migration — 0001 extensions (DATABASE_SCHEMA.md:29–34):** `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; vector; pgcrypto; citext;`
**Tests:** `alembic upgrade head` from empty DB succeeds; downgrade clean; 4 extensions present; `/ready` 200 only when head matches code.
**Acceptance:** Migrations run cleanly from empty DB (Phase 0 gate); extensions installed.
**Rollback/safety:** Additive/idempotent. App connects as least-privilege role (Slice 6).

---

### Slice 6 — DB roles + tenant-scoped DB helper + forced-RLS convention + raw-DB ban
**Objective:** Security keystone — non-`BYPASSRLS` app role; tenant helper setting tenant/actor/request context per txn; reusable forced-RLS migration helper; ban raw DB access outside repositories.
**Files (create):** `database.py` (extend: `tenant_db.session(tenant_id, actor_id, request_id)` async ctx manager), `repositories/base.py`, `migrations/versions/0002_roles_grants.py`, `migrations/helpers/rls.py`, CI lint/test banning raw `asyncpg.connect`/pool use outside helper+`repositories/`.
**Migration — 0002 roles:** `CREATE ROLE app_role NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;` (never BYPASSRLS); per-table grants added later.
**RLS policy form (DATABASE_SCHEMA.md:284–290 — verbatim):**
```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
CREATE POLICY <t>_tenant_isolation ON <t>
USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```
**Helper contract (AUTH_AND_RBAC.md:84–95):** open txn → `SET LOCAL app.current_tenant_id` (+ actor/request) → yield connection for repositories only → release. Workers use the same helper; fail closed if context missing.
**Tests:** helper sets/clears GUC within txn; `app_role` lacks BYPASSRLS (`pg_roles`); raw-connection ban test fails on out-of-bounds access.
**Acceptance:** All DB access via helper; least-privilege role; RLS helper reusable by every tenant-table migration.
**Rollback/safety:** Must not be weakened. Boot guard (Slice 9) asserts no BYPASSRLS + tenant context verifiable.

---

### Slice 7 — Core tenancy schema + identity mapping + forced RLS
**Objective:** `tenants`, `users`, `tenant_memberships` with forced RLS, tenant-first indexes, and managed-auth identity-mapping columns on `users`.
**Files (create):** `models/{tenant,user,membership}.py`, `repositories/{tenant,user,membership}_repo.py`, `migrations/versions/0003_tenancy_core.py`.
**Migration — 0003 tenancy core (DATABASE_SCHEMA.md:86–126, adapted for managed auth):** `tenants`; `users` (`email CITEXT UNIQUE`, **`identity_provider VARCHAR`, `provider_user_id TEXT` with `UNIQUE (identity_provider, provider_user_id)`**, no first-party `hashed_password` — managed auth owns credentials); `tenant_memberships` (`role CHECK IN ('owner','admin','marketer','reviewer','viewer','billing_admin')`, `UNIQUE (tenant_id, user_id)`, `ix_tenant_memberships_user_id`). Forced RLS on tenant-owned tables (`tenant_memberships`; `tenants` keyed by `id`). `users` is global identity (no tenant RLS) — access mediated by membership + object-auth.
**Tests:** cross-tenant denial (tenant A cannot see B's memberships); `FORCE ROW LEVEL SECURITY` via `pg_class`; tenant-first index present; `UNIQUE (tenant_id,user_id)` blocks dup membership; `UNIQUE (identity_provider, provider_user_id)` blocks dup identity.
**Acceptance:** Tenant A cannot read/update/delete B membership data; RLS forced; identity mapping enforced.
**Rollback/safety:** Reversible. RLS forced before any data path uses the tables.

---

### Slice 8 — Audit logging (append-only)
**Objective:** Immutable audit trail wired early so auth/RBAC/billing log from first commit.
**Files (create):** `models/audit_event.py`, `audit/service.py` (redaction + emit), `repositories/audit_repo.py` (INSERT/SELECT only), `migrations/versions/0004_audit_events.py`.
**Migration — 0004 audit_events (DATABASE_SCHEMA.md:257–268):** `id, tenant_id?, actor_user_id?, event_type, object_type, object_id, request_id, job_id, redacted_details JSONB, created_at` (server-set); indexes `(tenant_id,created_at DESC)`, `(tenant_id,object_type,object_id)`. `GRANT INSERT, SELECT ON audit_events TO app_role; REVOKE UPDATE, DELETE`. Optional trigger guard.
**Tests:** app role cannot UPDATE/DELETE; `created_at` server-set; `redacted_details` carries no secrets/PII; required events produce rows.
**Acceptance:** Append-only + immutable for app roles (Phase 0 gate); details redacted.
**Rollback/safety:** Immutability via grants (+optional trigger); never relax.

---

### Slice 9 — Mock/live adapter registry + production boot guard
**Objective:** Production-shaped adapter registry (mock vs live behind one interface) + startup boot guard in **backend and worker** that hard-fails unsafe config; wire into CI.
**Files (create):** `integrations/registry.py` (resolve by `APP_ENV`), `integrations/base.py`, `observability/boot_guard.py`, hook into `main.py` + `workers/__init__.py`; CI job running the guard against production-like config.
**Migration:** None.
**Boot guard — FAIL BOOT when `APP_ENV=production` and any true (CLAUDE env guard):** mock billing/mailbox/DNS/verifier/research outside a named demo env; webhook/app secrets blank/placeholder/missing/not sourced from AWS Secrets Manager; AWS KMS or AWS Secrets Manager unreachable/misconfigured; placeholder API/encryption/JWT/DB credentials; RLS disabled/not forced/missing on any tenant-owned table (`pg_class.relrowsecurity`/`relforcerowsecurity`); API/worker roles have BYPASSRLS (`pg_roles`); cannot verify DB tenant-context setup; migration version ≠ deployed code; required cookie/CORS/CSRF/HTTPS settings disabled. *(Secret-specific checks extended in Slice 10.)*
**Tests:** guard passes for `local` w/ mocks; **fails** for each unsafe production condition (one test each); runs in both entrypoints.
**Acceptance:** Unsafe prod/staging config hard-fails; mocks allowed only per CLAUDE env table; CI exercises guard.
**Rollback/safety:** The guard is a safety control — never bypass. Mock-in-prod blocked unless owner-approved named demo exception recorded.

---

### Slice 10 — Credential encryption & secret handling
**Objective:** Establish the end-to-end secret-handling pattern so no raw secret ever lands in the DB, logs, audit details, prompts, exports, bundles, errors, or any client/frontend response — and so production secrets use AWS Secrets Manager plus AWS KMS and are decrypted only inside approved credential/integration service methods.
**Files (create):** `integrations/secrets/manager.py` (resolve secrets from AWS Secrets Manager in prod; local/mock backend in dev, both via the same interface), `integrations/secrets/kms.py` (AWS KMS key management/envelope operations), `services/credentials.py` (the **only** module permitted to decrypt; exposes typed accessors, never returns raw secrets to callers/responses), `repositories/credential_repo.py`, extend `observability/boot_guard.py` (secret-safety checks), `migrations/versions/0005_integration_credentials.py` (schema stub only).
**Migration — 0005 integration_credentials (stub; exact columns flagged owner-decision):** `id, tenant_id, integration_connection_id?, credential_type, secret_ref TEXT NOT NULL` (reference only — e.g. `aws-secrets-manager://...`), `envelope_key_id TEXT`, `version INT`, `rotated_at?`, `rotation_due_at?`, `created_at, updated_at`. Forced RLS, tenant-first index. **DB stores `secret_ref` + encrypted metadata only — never plaintext or ciphertext of the secret itself.**
**Pattern (CLAUDE §10):** production secrets in AWS Secrets Manager; encryption/key management in AWS KMS; Postgres holds only `secret_ref` + safe metadata + version + rotation timestamps; **decrypt only inside `services/credentials.py` integration methods**; decrypted values never reach logs, prompts, audits, tool outputs, exports, frontend bundles, client responses, or error details.
**Boot-guard extension:** fail boot in prod if any required app secret (JWT/encryption/DB/webhook) is blank, placeholder, missing, or not sourced from AWS Secrets Manager; if AWS KMS/Secrets Manager is unreachable; if decryption path is misconfigured.
**Tests:** secret never appears in API response, log line, audit `redacted_details`, export, or error detail (assert via fixtures injecting a sentinel secret); decrypt works only through `services/credentials.py` (other layers cannot decrypt); DB row holds only `secret_ref`/metadata (no plaintext); rotation metadata updates bump `version`/`rotated_at`; boot guard fails on placeholder/missing/unsafe secret; mock secrets backend shares the live interface/error shapes.
**Acceptance:** No raw secret leaves the credentials service; DB persists references + metadata only; rotation metadata tracked; boot guard blocks unsafe secrets. Credential-encryption launch blocker satisfied (pattern + stub; live integration tables are Phase 1).
**Rollback/safety:** Decryption confined to one audited module. Never log/return secrets. Exact `integration_credentials` columns remain **owner-decision** before the first live integration — stub only here.

---

### Slice 11 — Idempotency foundation
**Objective:** Idempotency store + service for retry-safe risky actions with deterministic replay.
**Files (create):** `models/idempotency_key.py`, `services/idempotency.py`, `repositories/idempotency_repo.py`, `migrations/versions/0006_idempotency_keys.py`.
**Migration — 0006 idempotency_keys (DATABASE_SCHEMA.md:246–255):** `id, tenant_id?, actor_user_id?, key, request_hash, response_hash?, status_code?, locked_until?, expires_at, created_at`; `UNIQUE (tenant_id,key)`; `ix_idempotency_keys_expiry (expires_at)`.
**Replay (verbatim):** same key+body → stored response; same key+different body → `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`. Sources: API → `Idempotency-Key` header; worker → deterministic job key; webhook → provider event id.
**Tests:** dup same-body returns stored response (single effect); different body → reuse error; `locked_until` prevents concurrent double-processing; expiry index works.
**Acceptance:** No duplicated effects on retry (Phase 0 gate); replay semantics exact.
**Rollback/safety:** Must-never-postpone control; lock precedes any external effect.

---

### Slice 12 — Rate-limit foundation
**Objective:** Baseline rate-limiting middleware + service covering auth endpoints, webhook endpoints, risky API actions, and worker/job abuse controls — consumed by later slices.
**Files (create):** `middleware/rate_limit.py` (per-tenant + per-endpoint + per-IP), `services/rate_limit.py` (token-bucket/fixed-window; pluggable store), `services/job_throttle.py` (per-tenant/job-type concurrency + rate caps for the worker). Store: Redis (optional compose service) **or** a Postgres `rate_limit_counters` table (migration authored at execution time if Postgres chosen).
**Migration:** None by default; optional `rate_limit_counters` if Postgres-backed store chosen.
**Coverage (API_CONTRACT.md):** auth (IP+email), refresh, imports, agent/tool calls, sends, webhooks, billing. Response headers `RateLimit-Limit/Remaining/Reset`; over-limit returns the standard envelope with a rate-limit `code` + retry hint.
**Tests:** auth endpoint rate-limited by IP+email; webhook endpoint rate-limited; risky API action limited per tenant; worker job-throttle caps per-tenant concurrency/rate; limit headers present; over-limit returns envelope, not a raw 500.
**Acceptance:** Rate-limit gate enforced on auth, webhooks, risky actions, and worker jobs; consistent envelope + headers. Rate-limit launch blocker foundation satisfied.
**Rollback/safety:** Fails closed (deny on store outage for auth/webhooks). No PII in counters/keys.

---

### Slice 13 — Queue/outbox foundation + worker loop  ·  queue LOCKED (Postgres+SQS)
**Objective:** Durable Postgres jobs/outbox + worker loop that claims safely, sets tenant context, re-checks gates before executing. SQS production transport; local dev polls Postgres.
**Files (create):** `models/job.py`, `services/queue.py` (enqueue via outbox), `workers/loop.py` (`FOR UPDATE SKIP LOCKED`, lease, retry, DLQ; uses Slice 12 job-throttle), `repositories/job_repo.py`, `migrations/versions/0007_jobs.py`.
**Migration — 0007 jobs (outbox):** `id, tenant_id, job_key, job_type, status ('pending'→'dispatched'→'claimed'→'succeeded'|'failed'|'canceled'), payload JSONB, result?, error_message?, retry_count, max_retries, scheduled_for?, claimed_by_worker?, claimed_at?, locked_until?, created_at, updated_at`; `UNIQUE (tenant_id,job_key)`; indexes `(tenant_id,status)`, `scheduled_for`, `locked_until`. DLQ = `status='failed' AND retry_count >= max_retries` (+ SQS DLQ in prod).
**Worker rule (AUTH_AND_RBAC.md:94–95):** payload carries `tenant_id, actor_user_id|system_actor, correlation_id, job_id, idempotency_key, requested_permission`; worker **fails closed** without context, sets context via the helper, then **re-checks subscription, usage, permission, object access, rate limits** before executing.
**Tests:** retry-safe (crash mid-job → no dup effect, via Slice 11); DLQ on exhausted retries; `SKIP LOCKED` prevents double-claim; fail-closed without context; gate re-check at claim.
**Acceptance:** Queue/idempotency tests pass; no duplicate sends/billing effects (Phase 0 gate). Gate cleared.
**Rollback/safety:** Postgres outbox is the durable authority; transport swappable. Workers reuse the same services/gates as routes.

---

### Slice 14 — Auth & session (Clerk) + app-side mapping/revocation  ·  auth LOCKED=Clerk
**Objective:** Integrate Clerk; map Clerk identity → app `users`; bind tenant context from membership; keep a **minimal** app-side session/revocation record (only what app-side revocation + audit require); enforce platform-admin MFA + auth rate limits.
**Ownership split (clarified):**
- **Clerk owns:** credentials, login, sessions, password reset, email verification, MFA support, and primary auth security.
- **App owns:** `provider_user_id`/`identity_provider` mapping, tenant memberships, RBAC, object authorization, audit, billing gates, tenant context, DB RLS, and app-side session **revocation + membership-version** state.
- **Do not** build first-party password-reset / email-verification / refresh-token-rotation tables — the provider owns them. Build an app-side record **only** for revocation + audit.
**Files (create):** `services/auth.py` (verify provider token → resolve user via identity mapping → resolve membership), `middleware/auth.py` (token → session → tenant context), `routers/auth.py` (session exchange, logout, logout-all), `repositories/auth_session_repo.py`, `migrations/versions/0008_auth_sessions.py`.
**Migration — 0008 auth_sessions (minimal, justified by app-side revocation + audit):** `id, user_id, tenant_id?, provider_session_ref TEXT, membership_version INT, revoked_at?, created_at, expires_at`. (Identity columns live on `users` from Slice 7.) No raw tokens stored.
**Lifecycle the app enforces (AUTH_AND_RBAC.md:77–82):** logout / logout-all revoke app sessions; role change increments `membership_version` → forces re-auth/refresh; tenant lock/deletion invalidates access immediately; **platform-admin MFA required before external users/production** (provider feature, recommended for owners/admins); auth rate-limited (IP+email) via Slice 12. Provider-side reuse/rotation handled by the provider; app emits security audit on revocation/role change.
**Tests:** Clerk token validated → user resolved via `(identity_provider,provider_user_id)`; session→tenant mapping; logout/logout-all revoke app sessions; role change bumps `membership_version` and forces re-auth; tenant lock invalidates access; platform-admin login requires MFA; auth endpoints rate-limited.
**Acceptance:** Clerk login works; app-side revocation + membership-version + tenant binding enforced; admin MFA required. Gate cleared. (Refresh rotation + reuse detection owned by Clerk; verified at integration.)
**Rollback/safety:** No raw tokens/secrets stored. App-side session table is intentionally minimal — not a re-implementation of the provider.

---

### Slice 15 — RBAC + object-authorization + support-access grants
**Objective:** Service-layer permission enforcement + repository-layer object-ownership checks (anti-IDOR) + platform support-access grant model.
**Files (create):** `services/authz.py` (role/permission per capability matrix), `repositories/base.py` (extend: object-ownership assertion within tenant), `routers/platform/` (platform role + audit), `models/support_access.py`, `migrations/versions/0009_support_access.py`.
**Migration — 0009 admin_support_access (AUTH_AND_RBAC.md:99–103):** `reason, scope, approver, started_at, expires_at, revoked_at, support_access_id`; default grant 60 min; support actions log `support_access_id`; support cannot view secrets/raw credentials/full payment details/unredacted PII unless scoped + approved.
**Authorization order (AUTH_AND_RBAC.md:30–41):** session → membership → role/action permission → **object ownership** → billing/feature/usage → audit.
**Tests:** role-denial matrix (each capability × each role); **IDOR negative tests** — guessed/cross-tenant UUIDs → generic 404/403, no existence leak; platform routes reject non-platform roles; support grant time-limited + audited.
**Acceptance:** RBAC + object-auth tests pass (Phase 0 gate); IDOR blocked even with guessed IDs.
**Rollback/safety:** Frontend checks UX-only; never grant on RLS alone.

---

### Slice 16 — Mock billing state/access-gate skeleton  ·  mock-only MVP billing LOCKED
**Objective:** Build only the local MVP billing foundation: schema, tenant subscription/plan relationship, `tenant_status`, centralized gates, mock transitions, and deterministic tests. Real Stripe checkout, calls, webhooks, dunning, and money movement are out of Phase 0.
**Files (create):** `models/{plan,subscription}.py`, `services/billing_gate.py`, `services/mock_billing.py`, `repositories/subscription_repo.py`, `migrations/versions/0010_billing.py`.
**Migration — 0010 billing (DATABASE_SCHEMA.md:130–150):** `plans`; `tenant_subscriptions` with `provider DEFAULT 'mock'`, optional provider refs for future use, `tenant_status CHECK IN ('trialing','active','past_due','canceled','unpaid','inactive')`, `locked_reason, grace_ends_at, trial_ends_at, current_period_*`, `UNIQUE (provider,provider_subscription_id)`, `ix_(tenant_id,tenant_status)`. **Do not create `stripe_webhook_events` in local MVP.**
**Central gates:** all access routes through `is_active(tenant)` and `has_feature(tenant, key)`. Derived gates include `can_send`, `can_run_agents`, `can_create_campaign`, and `can_export`. Do not scatter billing if-checks across routes/services/workers.
**Lock policy:** `past_due` keeps access running during grace. `unpaid`, `canceled`, and `inactive` lock agent runs, cold email/SMS sending, paid ad spend, external paid API calls, and campaign creation; keep dashboard/data read access, exports, and dormant integrations available longer.
**Tests:** every mock state transition covered; gates block routes **and** workers at claim; `past_due` grace remains active; `unpaid`/`canceled`/`inactive` block paid/write/send actions; exports remain available when expected; no real Stripe checkout/calls/webhooks exist.
**Acceptance:** Billing gate works in routes + workers (Phase 0 gate); state cannot incorrectly grant paid access; deterministic mock billing tests pass.
**Rollback/safety:** Central gates are the only authority. Real Stripe is a later first-paying-client / production billing phase.

---

### Slice 17 — Compliance profile + suppression baseline (schema only)  ·  US MVP baseline locked
**Objective:** Schema-only baseline to satisfy the Phase 0 gate "compliance profile + suppression baseline exist." **No send/import logic** (Phase 1). MVP compliance baseline is United States; live sending remains gated by compliance review and owner approval.
**Files (create):** `models/{compliance_profile,suppression_entry,contact}.py`, `migrations/versions/0011_compliance_suppression.py`. Minimal RLS-scoped repos.
**Migration — 0011 (DATABASE_SCHEMA.md:154–187):** `tenant_compliance_profiles` (jurisdiction defaults to US for MVP/demo seed data; live approval still required); `contacts` (schema only — `tenant_id`, `email CITEXT`, status, `ux_contacts_tenant_email_active`, `deleted_at`); `suppression_entries` (`tenant_id, contact_id?, hashed_email?/email?, phone?, channel CHECK IN ('email','sms','all'), reason, source, reinstated_at?`; partial unique indexes on active suppressions). All forced RLS, tenant-first indexes.
**Tests:** forced RLS + cross-tenant denial on all three; suppression unique indexes block duplicate **active** suppression by email/phone/contact; compliance profile row creatable per tenant. *(Re-import survival + send-time suppression are Phase 1.)*
**Acceptance:** Compliance profile + suppression baseline exist w/ forced RLS (Phase 0 gate). No import/campaign/send behavior. US MVP baseline recorded; SMS remains post-MVP.
**Rollback/safety:** Schema-only; reversible. Does not start Phase 1 outreach.

---

### Slice 18 — Frontend wiring: managed-auth login, tenant context, billing banner, audit view
**Objective:** Connect shells to managed auth + backend foundation.
**Files (create/modify):** `frontend/app/(auth)/login/`, `frontend/lib/auth.ts` (managed-auth SDK), `frontend/app/(app)/layout.tsx` (tenant context + billing-state banner), `(app)/audit-logs/page.tsx`, `(app)/settings/team/page.tsx`, `frontend/lib/api-client.ts` (attach session + tenant header).
**Migration:** None.
**Tests:** managed-auth login → authenticated session; tenant header attached; billing-locked renders read-only banner + hides gated actions (UX only); audit view renders tenant-scoped rows.
**Acceptance:** User logs in (managed auth), lands in tenant context, sees billing state, views audit log. Role checks UX-only; all gating re-enforced server-side.
**Rollback/safety:** No secrets in bundle; no client-side authority.

---

### Slice 19 — Phase 0 test-gate suite + E2E smoke + evidence bundle + completion report
**Objective:** Assemble gate suite, run E2E smoke, produce completion report + evidence.
**Files (create):** `backend/tests/gates/` (migration-smoke, RLS-isolation, object-auth/IDOR, billing-lock, queue/idempotency, audit-immutability, boot-guard, **secret-redaction**, **rate-limit**), `e2e/phase0_smoke.spec.ts` (login → tenant context → billing banner → audit view), `docs/completion/PHASE_0_COMPLETION_REPORT.md`, enable full CI gate matrix.
**Migration:** None.
**Phase 0 "done" gates (TESTING_AND_AUDIT.md:48–60 — all must pass):** docs + ADRs exist · migrations run from empty DB · forced RLS enabled+tested · auth/session tests pass · RBAC/object-auth tests pass · billing gate works in routes+workers · queue/idempotency tests pass · compliance profile + suppression baseline exist · structured logs + audit immutable · CI blocks secrets/failing tests/migration drift. **Plus this plan's additions:** secret-redaction tests pass · rate-limit gate tests pass.
**Tests:** full gate suite green in CI; E2E smoke passes; evidence collected.
**Acceptance:** All gates pass; evidence bundle assembled; completion report drafted. **Phase 1 does not start** until accepted.
**Rollback/safety:** Go/no-go honored — any tenant-isolation, idempotency, webhook-verification, billing-grant, **or secret-leak** failure is **NO-GO**.

---

## 3. Phase 0 launch blockers addressed during implementation

| Blocker | Slice |
|---|---|
| Production boot guard (hard-fail unsafe config) | 9 (+10 secrets) |
| Forced RLS + tenant context, no BYPASSRLS | 6, 7 (asserted 9, 19) |
| App-side session revocation + membership-version (managed-auth model) | 14 |
| **Platform-admin MFA** | 14 (verified 19) |
| RLS/object-auth automated tests | 7, 15, 19 |
| Mock billing state machine + centralized gates | 16 |
| Idempotency prevents duplicate sends/billing | 11, 13 |
| **Rate limits + abuse protection** (auth, webhooks, risky actions, jobs) | 12 |
| **Credential encryption + Secrets Manager + KMS** | 10 |
| Audit immutability | 8 |
| Live webhooks rejected without verification | 16 |
| CI blocks secrets/failing tests/migration drift | 1, 19 |

**Must-never-postpone (NO-GO if violated):** tenant isolation · idempotency prevents duplicates · webhooks verified · billing state cannot grant paid access incorrectly · agent cannot send/access secrets/bypass tool permissions · **no secret leakage** · backup-restore drill exists (ops, scheduled separately).

---

## 4. Explicitly out of scope until Phase 1+ (do-not-build)

CSV/campaign import **functionality** (contacts schema stub only in Slice 17) · AI drafting / agent run tables / RAG / groundedness / re-grounding · **send-gate functionality**, no-send reason codes, mailbox pool, warm-up, throttles, deliverability dashboard · outbound-message/send-intent send behavior · real Stripe checkout/calls/webhooks/dunning/money movement · real SMS (A2P 10DLC/Twilio), Google/Meta Ads, Google Business Profile, advanced CRM, SEO/AI-search rank tracking · real mailbox integration beyond adapter contracts + mock · live scraping / paid research · auto live sends from signals · Slack/internal alerts · full multi-plan self-serve pricing UI · Phases 2–6. **Do not start Phase 2 until the Phase 0+1 completion report is accepted.**

---

## 5. Risks and owner decisions

**Open owner decisions (Needs owner decision — do not guess):**
1. **Counsel-approved legal/privacy/outreach/unsubscribe/data-use language** — required before live sending.
2. **Approved live research/scraping/paid-provider sources** — required before live research.
3. **Exact `integration_credentials` columns** — Slice 10 ships a stub; finalize columns before the first live integration.
4. **Production mock-provider exception** — none by default; record owner-approved named-demo exception if needed (boot guard, Slice 9).
5. **Rate-limit store** — Redis (compose) vs Postgres counter table (Slice 12).
6. **Demo tenant seeding** — automatic vs manual; record count (Slice 19 E2E).
7. **First-paying-client production billing details** — Stripe products/prices, plan entitlements, and rollout evidence.

**Risks:**
- **Credential-encryption DDL not fully specified in docs** — mitigated by Slice 10 establishing AWS Secrets Manager/KMS pattern + stub; exact columns owner-gated.
- **Managed-auth responsibility boundary** — Slice 14 keeps the app-side session table intentionally minimal (revocation + audit + membership-version only); confirm the provider covers tenant-scoped session invalidation, else expand the app-side record.
- **`users` global RLS** — `users` is global identity (no tenant RLS); access mediated by membership + object-auth. Assumed in Slice 7.

---

## 6. Recommended first implementation slice

**Slice 1 — Repo scaffolding, tooling, CI skeleton.** ADR-independent, unblocks every other slice, and immediately installs the guardrails (lint, type-check, secret scan, CI) that keep all security-critical work honest. No DB, no secrets, no providers — lowest risk, highest leverage. Slices 2–4 follow/parallelize; the security core (5 → 6 → 7) then begins. Close **Slice 0** in parallel so gated slices are unblocked by the time the critical path reaches them.

---

## Verification (how Phase 0 is proven end-to-end)

1. `alembic upgrade head` from empty DB succeeds; 4 extensions present (5).
2. RLS isolation: tenant A cannot see B on every tenant-owned table; FORCE confirmed via `pg_class` (7, 17, 19).
3. Object-auth/IDOR: guessed cross-tenant UUIDs → generic 404/403, no existence leak (15).
4. Billing-lock: locked `internal_access_state` blocks routes + a worker job at claim (16).
5. Queue/idempotency: forced retry/crash → no duplicate effect; replay exact (11, 13).
6. Audit-immutability: app role cannot UPDATE/DELETE `audit_events` (8).
7. **Secret-redaction:** sentinel secret never appears in responses/logs/audit/exports; decrypt only via credentials service (10).
8. **Rate-limit:** auth/webhook/risky-action/job limits enforced with envelope + headers (12).
9. Boot-guard: each unsafe production condition (incl. secrets) hard-fails boot in backend + worker (9, 10).
10. E2E smoke: managed-auth login → tenant context → billing banner → audit view (18/19).
11. CI runs full gate matrix + secret scan + migration smoke + Docker smoke green (19).
12. Completion report + evidence bundle assembled for owner go/no-go; Phase 1 gated on acceptance (19).
