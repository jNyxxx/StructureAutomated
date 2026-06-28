# Documentation Manifest (Tracker)

**Purpose:** Tracking file for the documentation effort. **Not** one of the 20 implementation docs and not part of the build. Tracks the final doc set, source sections, size targets, batch order, status, owner decisions, and merge/avoid notes.
**Source of truth:** `AutomatedStructure_Final_Master_Build_Guide.md` (Markdown only; the PDF is excluded per Appendix A). Per Appendix A, this guide wins over older sources unless stricter signed legal policy, provider requirements, or production-incident decisions apply.
**Status:** DOC-2 complete — all 20 implementation docs created and accepted as **Accepted draft**; Batches 0–7 done. DOC-3 review accepted; DOC-4 cleanup applied. This manifest is the tracker and is **not** counted among the 20 implementation docs.

---

## Conventions (apply to all 20 docs)

- **Required header block** at the top of every implementation doc **except `README.md`**: `Purpose` · `Source sections` · `Status` · `Related docs`. README uses a project-overview format; ADRs use the ADR header (`Status` · `Date`).
- **Status values:** implementation docs use `Draft` · `Required` (must exist, not yet written) · `Owner decision needed` (blocked on a decision) · `Accepted draft` (created and accepted in review, pending implementation). **ADRs** use normal ADR statuses: `Proposed` · `Accepted` · `Superseded`.
- **Size targets are ceilings/guidelines, not minimums (lines):** Small ≤180 · Medium ≤350 · Large ≤650 · ADR ≤120 · README ≤160. Complete, lean docs **below** the old "floor" are acceptable — never pad to hit a line count. CLAUDE.md: strict and practical, not essay-style.
- **Reference, don't duplicate.** Canonical locked-stack lives only in `ARCHITECTURE.md`; ADRs hold the *decision*, partner docs link to the ADR.
- Markdown only. Any non-Markdown change → stop and ask.

---

## Final doc set (20 implementation docs)

| # | File | Purpose | Source § | Size | Batch | Status |
|---|------|---------|----------|------|-------|--------|
| 1 | `CLAUDE.md` | Repo + agent rules: source-of-truth order, non-negotiable engineering rules, env/prod-boot safety guard, mock-mode rules, layer rules, credential-encryption rule, preservation checklist | 2, 6, 10, 27 | M | 1 | Accepted draft |
| 2 | `docs/ARCHITECTURE.md` | System architecture, component responsibilities, trust boundaries, canonical locked stack, project + App Router structure | 4, 5, 10, 18 | M | 1 | Accepted draft |
| 3 | `docs/DATABASE_SCHEMA.md` | DB contract: tables, status domains, DDL, composite indexes, forced RLS, outbox/send-intent uniqueness, acceptance checklist | 7, 16 | L | 2 | Accepted draft |
| 4 | `docs/API_CONTRACT.md` | Endpoint groups, common responses, error envelope, pagination/filtering, idempotency, rate limits | 11, 10 | M | 2 | Accepted draft |
| 5 | `docs/AUTH_AND_RBAC.md` | Users/roles, authorization rule, object auth, tenant isolation (HTTP+worker), support access, session lifecycle (refresh rotation, reuse detection, revocation) | 3, 8, 9 | M | 2 | Accepted draft |
| 6 | `docs/BILLING_STATE_MACHINE.md` | Mock MVP billing states, tenant status, centralized gates, and later production Stripe/dunning notes | 12 | M | 3 | Accepted draft |
| 7 | `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md` | Send gate checks, no-send reason codes, compliance profile, suppression/unsubscribe, duplicate-send prevention, mailbox pool/warm-up/throttle/deliverability, CSV import + list verification | 14, 15 | M/L | 3 | Accepted draft |
| 8 | `docs/AI_SAFETY_AND_GROUNDEDNESS.md` | LangGraph flow, agent state, tool registry, prompt-injection defense, groundedness gate + re-grounding after edits, human review queue, cost controls, RAG/research governance | 13, 16 | M | 3 | Accepted draft |
| 9 | `docs/WORKERS_QUEUE_AND_WEBHOOKS.md` | Queue decision, SQS/Postgres outbox, worker runtime + worker tenant context, jobs/retries/idempotency/DLQ, n8n boundaries, inbound webhook verification | 17, 8 | M | 4 | Accepted draft |
| 10 | `docs/PRIVACY_AND_RETENTION.md` | Privacy posture, retention defaults, do-not-store rules, export/delete/PII + vector purge | 21, 16 | S/M | 4 | Accepted draft |
| 11 | `docs/FRONTEND_GUIDE.md` | Frontend rules, required MVP pages, review-diff view (human-review UI), accessibility | 18 | S/M | 4 | Accepted draft |
| 12 | `docs/OPERATIONS_RUNBOOK.md` | Two sections: (a) Observability — log shape, alerts, response; (b) DevOps — compose, CI jobs, deploy pipeline, migration + rollback, backup/restore drill | 19, 20 | M | 5 | Accepted draft |
| 13 | `docs/TESTING_AND_AUDIT.md` | Required test suites, phase completion gates, completion-report template, RLS/isolation + DB acceptance tests, launch evidence bundle | 23, 7, 8, 25 | M | 5 | Accepted draft |
| 14 | `docs/PHASE_0_1_IMPLEMENTATION_PLAN.md` | Phased checklist: Phase 0 foundation, Phase 1 MVP, non-goals/do-not-build, start-here steps, forward roadmap | 1, 24, 26 | M | 6 | Accepted draft |
| 15 | `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` | Direct blocker + owner-decision checklist, go/no-go rule, pilot policy | 25, A | M | 6 | Accepted draft |
| 16 | `README.md` | Project overview, locked-stack (brief), local-setup pointer, doc navigation | 1, 4, 26 | S | 6 | Accepted draft |
| 17 | `docs/ADRs/ADR_AUTH_PROVIDER.md` | Decision: Clerk managed auth | 9, 25 | ADR | 7 | Accepted |
| 18 | `docs/ADRs/ADR_QUEUE_TRANSPORT.md` | Decision: queue transport (SQS vs Postgres outbox) | 17 | ADR | 7 | Accepted (locked) |
| 19 | `docs/ADRs/ADR_BILLING_ACCESS_STATES.md` | Decision: mock-only MVP billing access states and later production Stripe/dunning boundary | 12, 25 | ADR | 7 | Accepted |
| 20 | `docs/ADRs/ADR_COMPLIANCE_JURISDICTION.md` | Decision: United States MVP compliance baseline and first US target market | 21, 25 | ADR | 7 | Accepted |

---

## Phase 1 evidence files

Produced by P1-13 (E2E smoke + evidence update). Not counted among the 20 implementation docs.

| File | Purpose |
|------|---------|
| `docs/evidence/phase-1-final-verification.md` | Slice completion table, E2E smoke test results, quality gate outputs, migration state, deferred items |
| `docs/evidence/phase-1-readiness-checklist.md` | Structured checklist covering all CLAUDE.md rules, gates, multi-tenancy, mock mode, idempotency, and Phase 1 deferred items |
| `docs/evidence/frontend-final-verification.md` | Frontend final verification covering FE-0 through FE-16, route and component coverage, quality gates, local/mock limits, and production blockers |
| `docs/evidence/frontend-readiness-checklist.md` | Frontend readiness checklist covering slices, pages, reusable systems, locked/demo behavior, accessibility/mobile checks, and next backend/API work |

---

## Phase 2 evidence files

Produced by Phase 2 backend API completion (P2-1 through P2-8). Not counted among the 20 implementation docs.

| File | Purpose |
|------|---------|
| `docs/evidence/phase-2-backend-api-final-verification.md` | Route group table, mounted routers list, OpenAPI count (44 paths / 51 operations), quality gate results, security/gating summary, mock/local-only summary, deferred blockers, verdict |
| `docs/evidence/phase-2-backend-readiness-checklist.md` | Structured checklist covering CLAUDE.md rules, quality gates, route coverage, multi-tenancy/RLS, mock-mode discipline, and deferred items |
| `docs/evidence/phase-2-frontend-final-verification.md` | Frontend Phase 2 read-only final verification covering FE-P2-1 through FE-P2-7b, quality gates, safety audit, local/mock limits, and deferred blockers |
| `docs/evidence/phase-2-frontend-readiness-checklist.md` | Frontend Phase 2 readiness checklist covering read-only surfaces, fallback behavior, locked actions, test results, and Phase 3 approval requirement |
| `docs/evidence/phase-2-final-verification.md` | Combined Phase 2 backend + frontend final verification summary and final local/mock verdict |
| `docs/evidence/phase-2-exit-completion.md` | Phase 2 exit ("P2-exit") close-out: localhost e2e enablement layer (mock auth, strict backend mode, mock-write wiring), re-run gates (515 backend / 122 frontend), live boot smoke (8/8), honest live-DB/browser-e2e limitations, deferred Phase 3 items |

---

## Phase 3 planning (not counted among the 20 docs)

The Phase 3 analog of doc #14 (`PHASE_0_1_IMPLEMENTATION_PLAN.md`). Planning artifact added after owner approval to enter Phase 3; the locked 20-doc set is unchanged.

| File | Purpose |
|------|---------|
| `docs/PHASE_3_IMPLEMENTATION_PLAN.md` | Phase 3 scope lock + slice plan (P3-0…P3-7) with class, acceptance criteria, stop gates, required owner decisions, deferred list, and non-weakening invariants. Owner approval recorded in `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` §2. |

---

## Phase 3 evidence files (not counted among the 20 docs)

| File | Purpose |
|------|---------|
| `docs/evidence/phase-3-1-production-readiness-audit.md` | P3-1 read-only production-readiness audit: method, re-run gate results (515 backend / 122 frontend), readiness findings (boot-guard/billing/sending/secrets READY; RLS/auth/deploy gaps), stop-gates confirmed, controlled_demo governance note, recommended first hardening slice, honest limits. Verdict: ready for first prod-hardening slice, zero true blockers. |
| `docs/evidence/phase-3-1a-boot-guard-hardening.md` | P3-1a first hardening slice: boot-guard tenant-owned RLS coverage expanded 2 → 29 tables (count corrected 23 → 29 with evidence); controlled_demo owner-approval attestation added (fails closed in production); 10 new boot-guard tests. Gates: backend 525 / frontend 122 PASS. No production / providers / sending / migrations enabled. |
| `docs/evidence/phase-3-2-live-db-smoke.md` | P3-2 live DB smoke + seeded local demo: compose db/backend, alembic at head `00021_outcomes`, 29/29 boot-guard tables RLS-forced, tenant isolation proven under an ephemeral least-privilege role (A=1/B=0), mock tenant billing gates active, protected API smoke (44 paths / 51 ops) all 200. Honest local finding: `app_user` is superuser/bypassrls (image default) — RLS enforced via least-privilege role + repo `tenant_id` predicates; prod boot guard blocks superuser. Gates: backend 525 / frontend 122 PASS. No production / providers / sending enabled. |
| `docs/evidence/phase-3-3a-clerk-auth-readiness-plan.md` | P3-3a Clerk production auth readiness: current auth state (mock-only, DI seam ready), production Clerk JWT verifier contract (`ClerkJwksVerifier`, JWKS/RS256, claims mapping, failure modes), required env/secrets (`AUTH_PROVIDER_ISSUER`/JWKS/audience + frontend Clerk vars), boot-guard gap identified, implementation slices P3-3b→P3-3e defined, 6 owner decisions gating P3-3b. Status: owner decision needed. No code changed, no real secrets, production not enabled. |
| `docs/evidence/phase-3-3c-managed-auth-wiring.md` | P3-3c backend managed Clerk AuthService wiring: `ClerkJwksVerifier` singleton wired at startup, per-request DB-backed `UserRepository`/`MembershipRepository`/`AuthSessionRepository` via `auth_context_session()`, local/mock path unchanged, `enforce_mfa()` wired (no-op until `platform_admin` added to RBAC), 6 owner decisions recorded, 570 backend tests pass. Production not enabled, no real secrets, no frontend Clerk widget. |
| `docs/evidence/phase-3-3b-clerk-verifier-implementation.md` | P3-3b backend Clerk JWKS verifier: `ClerkJwksVerifier` (RS256/JWKS via `cryptography`, injectable JWKS source, fails closed, never falls back to mock) behind the existing `ClerkTokenVerifier` Protocol; managed-auth `Settings` + `.env.example` placeholders; boot-guard `_auth_failures()` (mock auth blocked in prod incl. under controlled_demo, issuer/JWKS https-non-localhost, secret/publishable non-placeholder); `enforce_mfa()` primitive (inert — no `platform_admin` role in RBAC yet); 6 owner decisions recorded. Gates: backend 566 / frontend 122 PASS (+ build). No production cutover, no real secrets, `.env` untouched, frontend Clerk widget unchanged, auth chain/RLS unchanged. |
| `docs/evidence/phase-3-3d-platform-admin-rbac-plan.md` | P3-3d platform_admin RBAC decision (docs-only): role-model inspection (3-source drift, support role vestigial, DB CHECK literal SQL → migration required), MFA mechanism confirmed fail-closed and fully tested, owner decision resolved (tenant-scoped Option A, permissions limited to platform routes, no implicit tenant data/RLS-bypass/owner powers, MFA mandatory), P3-3e implementation spec (migration + authz.py + membership.py + tests), stop-gates. No code/migration/tests written. Gates: backend 570 / frontend 122 unchanged. |
| `docs/evidence/phase-3-3e-platform-admin-mfa-implementation.md` | P3-3e platform_admin role implementation: `CAN_ACCESS_PLATFORM = "platform:access"` added (isolated platform namespace); `platform_admin` added to `ROLE_PERMISSIONS`, `ROLES` tuple, and DB CHECK constraint via migration `00022_platform_admin_role` (down_revision `00021_outcomes`); `enforce_mfa()` now active in live flow (mfa_verified=False → MFA_REQUIRED 403); support drift deferred (intentional, grant-based model preserved); 6 new tests. Gates: backend 576 / frontend 122 PASS. No production / real secrets / frontend Clerk / providers / sending enabled. |
| `docs/evidence/phase-3-3f-clerk-frontend-integration-plan.md` | P3-3f frontend Clerk integration plan (docs-only): frontend auth inspection (`@clerk/nextjs` not installed; `ClerkFrontendProvider` stub with `value?` injection point; `FrontendAuthState` adapter; no api-client/tenant-context changes needed); integration design (`clerk-real.tsx` adapter, root-layout conditional mount, catch-all sign-in/up routes); env/config checklist (frontend + backend vars); tenant-selector gap documented (owner decision deferred); 18-step real-JWT smoke checklist; blocker list. Verdict: blocked on Clerk dev project (owner action). Gates: backend 576 / frontend 122 unchanged. No code changes. |
| `docs/evidence/phase-3-4a-rate-limits-abuse-protection-plan.md` | P3-4a rate limits and abuse protection inspection/plan (docs-only): existing middleware/service/backend/policies/JobThrottle mapped; critical no-op bug found in `sending.py`/`followups.py`; per-endpoint gaps identified; P3-4b shared backend + endpoint limit plan defined; Redis deferred to P3-4c. No code changes. |
| `docs/evidence/phase-3-4c-redis-rate-limit-backend.md` | P3-4c Redis rate-limit backend: `RedisRateLimitBackend` with atomic Lua `INCR`/`EXPIRE`/`TTL`, lazy `redis.asyncio` import, config selection via `RATE_LIMIT_BACKEND`/`RATE_LIMIT_REDIS_URL`, production boot guard requiring Redis, fake-Redis tests, `.env.example` placeholders, runbook update. Gates: backend ruff/black/mypy PASS, backend 592 PASS, frontend lint/typecheck/test/build PASS (122 tests). No production deploy or real providers/sending/Stripe/SMS/live scraping. |
| `docs/evidence/phase-3-4d-redis-runtime-smoke.md` | P3-4d Redis runtime smoke + ops evidence: Docker Desktop started; local `docker compose --profile cache` Redis + backend smoke container (`APP_ENV=local`, `RATE_LIMIT_BACKEND=redis`, `RATE_LIMIT_REDIS_URL=redis://redis:6379/0`) proved backend boot, `/health` 200, `/live` 200, `/ready` local migration out-of-date status, runtime `RedisRateLimitBackend`, HTTP 429, Redis key PII safety, tenant-scoped isolation, TTL reset, and Redis-down behavior (standard 500, not fail-open; explicit 503/readiness deferred). Gates: backend ruff/black/mypy PASS, backend 592 PASS, frontend lint/typecheck/test/build PASS (122 tests). Docs-only. |
| `docs/evidence/phase-3-4e-redis-readiness-error-hardening.md` | P3-4e Redis readiness/error hardening: backend counter failures now return sanitized `503 RATE_LIMIT_BACKEND_UNAVAILABLE`; `/ready` reports `rate_limit_backend` and Redis `ok/unavailable` when configured; tests cover fail-closed/no-leak behavior and readiness modes. Runtime smoke confirmed Redis-up readiness, Redis-down readiness, Redis-down 503, and Redis-up 429. Gates: backend ruff/black/mypy PASS, backend 598 PASS, frontend lint/typecheck/test/build PASS (122 tests). |
| `docs/evidence/phase-3-4f-rate-limit-abuse-protection-acceptance.md` | P3-4f rate-limit / abuse-protection acceptance closeout: accepts P3-4a→P3-4e as green, records commit chain, completed scope, final gate results (backend ruff/black/mypy PASS; backend 598 PASS; frontend lint/typecheck/test/build PASS with 122 tests), honest limits, and future production Redis provisioning requirement. Docs-only. |
| `docs/evidence/phase-3-5a-real-sending-provider-design.md` | P3-5a real sending/provider design inspection + stop-gate plan: documents current mock-only sending state, existing send gates/DB records, missing live-provider pieces, provider Protocol/registry/mock-real boundary, secret-ref pattern, required safety chain, owner decisions, config/boot-guard requirements, P3-5b→P3-5f slice plan, and tests needed. Docs-only; no provider code, credentials, network calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-5b-provider-interface-boundary.md` | P3-5b provider interface + mock/live boundary hardening: adds `EmailSendProvider` Protocol, safe request/result DTOs, network-free mock adapter, fail-closed registry/factory, safe config defaults, production boot-guard checks, and tests proving provider names/live sending fail closed. Existing send-intent response remains mock-only. No provider SDKs, live adapters, credentials, provider calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-5c-provider-selection-secrets-config.md` | P3-5c provider selection + secrets/config design: compares Amazon SES, SendGrid, Postmark, Mailgun, and Resend; records non-final first-pilot recommendation; defines secret-ref-only config, AWS Secrets Manager/KMS path, DNS/subdomain workflow, signed/idempotent webhook design, owner decisions, future slice plan, and tests needed. Docs-only; no provider code, SDKs, credentials, provider calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-5d-real-sending-owner-decision-packet.md` | P3-5d real sending owner decision packet: owner-fillable approval checklist for provider, sending domain/subdomain, DNS owner, sender identity, legal/unsubscribe copy, send caps, sandbox/internal smoke, webhook scope/signing, deliverability owner, incident owner, and provider account owner. Blocks adapter/live-send work until answered. Docs-only; no code, SDKs, credentials, provider calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-5e-owner-approval-resend-roadmap.md` | P3-5e owner approval + Resend roadmap: records the owner's answers to the P3-5d packet — **Resend** selected as main email provider; sending subdomain `outreach.automatedstructure.com`, sender identity, required unsubscribe footer copy, conservative first-pilot caps (tenant 10/hr·50/day, campaign 50/day, mailbox 25/day), normalized webhook event scope + signature/idempotency, deliverability/emergency-stop/provider-account ownership, internal-only first smoke. Lists 8 outstanding pre-smoke values and the post-approval roadmap (P3-5f adapter skeleton → P3-5g secret/DNS/webhook → P3-5h internal smoke → P3-5i external, separate approval). Real sending stays disabled; adapter not built. Docs-only; no code, SDKs, credentials, env, provider calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-7a-deployment-ops-readiness-plan.md` | P3-7a deployment/ops readiness inspection + staging plan: documents current local-only Docker/Compose state, backend/frontend/worker/DB/Redis/secrets/observability readiness, production blockers, AWS-oriented staging architecture proposal, local/staging/production environment matrix, owner/operator values needed, P3-7b→P3-7g slice plan, and required staging smoke checks. Docs-only; no app/config/migration/env changes, AWS work, production cutover, Resend SDK/API/live adapter, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-7b-production-dockerfile-hardening.md` | P3-7b production Dockerfile hardening: adds production-specific backend/frontend Dockerfiles, hardens backend/frontend `.dockerignore`, enables Next standalone output, records backend/frontend gate results, worker runtime strategy, Docker daemon unavailable limit, remaining deployment blockers, and safety confirmation. No deployment, AWS work, production enablement, secrets, Resend/live sending, Stripe, SMS, live scraping, provider SDK, or registry push. |

---

## Supplementary process notes (not counted among the 20 docs)

| File | Purpose |
|------|---------|
| `docs/ENGINEERING_SESSION_GUARDRAILS.md` | Pre-flight + in-session guardrails: verify clean/stable tree before work, single-writer rule, no force-push, preserve local/mock notices and gate labels, re-run checks before commit |

---

## Folded / avoided (no standalone doc)

| Master § | Folded into | Why |
|----------|-------------|-----|
| §6 Mock Mode | `CLAUDE.md` | Hard rule, too small to stand alone |
| §22 Required Repo Docs | *this manifest* | Manifest fulfills the role |
| §27 Preservation Checklist | `CLAUDE.md` | Agent guardrail |
| §24 Roadmap | `PHASE_0_1_IMPLEMENTATION_PLAN.md` | Roadmap section |

## Merge/avoid notes (vs original 22-file manifest)

- **MERGE** `PROJECT_STRUCTURE` → `ARCHITECTURE` (file tree is a section).
- **MERGE** `WORKERS_AND_QUEUE` + `WEBHOOKS_AND_N8N` → `WORKERS_QUEUE_AND_WEBHOOKS` (single ~44-line §17; splitting over-fragments).
- **MERGE** `OBSERVABILITY_RUNBOOK` + `DEPLOYMENT_RUNBOOK` → `OPERATIONS_RUNBOOK` (two clear sections).
- **ADD** `FRONTEND_GUIDE` (§18 MVP pages + review-diff UI were unmapped — implementation-critical for Phase 1).

---

## Batch order

All batches complete — DOC-2 finished:

- **0.** Rewrite this manifest ✅
- **1.** `CLAUDE.md` · `ARCHITECTURE.md` ✅
- **2.** `DATABASE_SCHEMA.md` · `API_CONTRACT.md` · `AUTH_AND_RBAC.md` ✅
- **3.** `BILLING_STATE_MACHINE.md` · `EMAIL_COMPLIANCE_AND_SEND_GATE.md` · `AI_SAFETY_AND_GROUNDEDNESS.md` ✅
- **4.** `WORKERS_QUEUE_AND_WEBHOOKS.md` · `PRIVACY_AND_RETENTION.md` · `FRONTEND_GUIDE.md` ✅
- **5.** `OPERATIONS_RUNBOOK.md` · `TESTING_AND_AUDIT.md` ✅
- **6.** `PHASE_0_1_IMPLEMENTATION_PLAN.md` · `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` · `README.md` ✅
- **7.** 4 ADRs (each tiny; collectively ≈ one doc) ✅

---

## Owner decisions required (from §25) — lands in `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`

| Decision | Recommended default | Needed by | Doc home |
|----------|---------------------|-----------|----------|
| SMS legal wording | Counsel-approved only | Phase 3 | EMAIL_COMPLIANCE |
| CRE research source approval | Public/mock for MVP; legal review before live scraping | Live research | AI_SAFETY / PRIVACY |
| Support access approval | Owner/super-admin grant + audit | External users | AUTH_AND_RBAC |
| Production mock-provider exception | No exception by default | Before any prod demo on mock providers | CLAUDE |
| First-paying-client production billing | Stripe products/prices, plan entitlements, webhook/dunning rollout | First paying client | BILLING / ADR_BILLING |

## Launch blockers (from §25) — mirrored in `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`

Legal review (compliance) · Clerk production configuration + platform-admin MFA (auth) · centralized mock billing gates (billing) · rate limits/abuse (security) · credential encryption + AWS Secrets Manager/KMS (security) · RLS/object-auth tests (security) · backup restore drill (devops) · in-product observability + LangSmith faithfulness logging (SRE/AI) · privacy export/delete/vector purge (privacy) · production boot guard missing (security/ops).

---

## Conflicts / gaps

- **Conflicts:** None at product/architecture level (Appendix A). If older source files disagree, this guide wins unless stricter legal/provider/incident rule.
- **Open owner decisions:** limited to genuinely unresolved launch/future items above; Clerk, US compliance baseline, AWS Secrets Manager/KMS, and mock-only MVP billing are owner-confirmed.
- **Gaps:** none beyond the listed owner decisions. No requirements invented.
