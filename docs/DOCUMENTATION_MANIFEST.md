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

## Phase 4 planning (not counted among the 20 docs)

Phase 4 is the staging and first-paying-client pilot readiness program. It is a new planning track after Phase 3 final handoff and P3-Audit; the locked 20-doc set is unchanged.

| File | Purpose |
|------|---------|
| `docs/PHASE_4_IMPLEMENTATION_PLAN.md` | Phase 4 scope lock + slice plan (P4-0…P4-10), required owner/operator values, entry/exit criteria, non-goals, hard stops, and verification requirements. P4-1 intake complete; P4-2/P4-4/P4-5 remain blocked until required values are locked or explicitly deferred. No deployment, provider enablement, registry push, billing money movement, SMS, or live scraping is approved. |
| `docs/integrations/N8N_WORKFLOW_PLAN.md` | n8n role, boundaries, and future workflow catalog (docs-only; zero workflows built; owner decisions pending). |

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
| `docs/evidence/phase-3-5e-owner-approval-resend-roadmap.md` | P3-5e owner approval + Resend roadmap: records the owner's answers to the P3-5d packet — **Resend** selected as main email provider; sending subdomain `outreach.automatedstructure.com`, sender identity, required unsubscribe footer copy, conservative first-pilot caps (tenant 10/hr·50/day, campaign 50/day, mailbox 25/day), normalized webhook event scope + signature/idempotency, deliverability/emergency-stop/provider-account ownership, internal-only first smoke. Lists 8 outstanding pre-smoke values and the post-approval roadmap (P3-5f adapter skeleton → P3-5g secret/DNS/webhook → P3-5h internal smoke → P3-5i external, separate approval). Real sending stays disabled; adapter not built in P3-5e. Docs-only; no code, SDKs, credentials, env, provider calls, production, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-5f-resend-adapter-skeleton.md` | P3-5f Resend adapter skeleton: adds disabled/fail-closed `ResendEmailSendProvider` behind the existing provider boundary; preserves default mock behavior; prevents Resend-to-mock fallback; adds config/cap/webhook-ref checks and production/staging live-send boot-guard checks; records tests/gates/Docker builds. No Resend SDK, network call, credentials, live send, deployment, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-5g-resend-webhook-verification.md` | P3-5g Resend webhook verification and normalization foundation: adds fail-closed Resend/Svix signature verifier, safe event normalizer, idempotency store boundary, and `POST /api/v1/webhooks/resend` route skeleton; records route behavior, boot-guard webhook-secret requirements, tests/gates, and honest limits. No Resend SDK/API call, real credentials, live send, deployment, Stripe, SMS, open/click tracking, or live scraping. |
| `docs/evidence/phase-3-5h-prep-internal-resend-smoke.md` | P3-5h-prep internal-only Resend smoke preparation: docs-only checklist defining required concrete values, required gates, one-email internal-only scenario, rollback/emergency stop, later real-smoke evidence bundle, and hard-stop conditions. No code, real send, Resend API call, credentials, deployment, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-5i-resend-secret-readiness-contract.md` | P3-5i Resend secret-resolution and smoke readiness contract: docs-only contract defining secret-ref requirements, DNS/domain proof, smoke owner values, gate readiness, `config_ready` / `smoke_ready` / `send_ready` / `production_ready` states, secret-resolution boundary, later evidence bundle, and hard stops. No code, Resend SDK/API call, credentials, deployment, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-5j-dual-sending-layer-scope-correction.md` | P3-5j dual sending-layer scope correction, code guard, config alignment, emergency-stop |
| `docs/evidence/phase-3-6a-stripe-billing-owner-decision-packet.md` | P3-6a Stripe / real billing owner decision packet: owner-fillable decision form for provider choice, billing mode, plans/pricing, access rules, payment failure, refund/chargeback, Stripe object scope, webhook scope, config refs, safety requirements, owners, missing items, proposed P3-6b→P3-6f slices, and hard stops. Docs-only; no Stripe SDK/API call, credentials, checkout, webhook, real billing, money movement, deployment, SMS, or live scraping. |
| `docs/evidence/phase-3-6b-stripe-config-secret-readiness-contract.md` | P3-6b Stripe config / secret-readiness contract: docs-only contract defining Stripe refs, required URLs, test-first mode defaults, product/price configuration, billing readiness states, central gate requirements, webhook readiness, hard stops, and remaining owner answers. No Stripe SDK/API call, checkout, webhook, real billing, money movement, deployment, SMS, or live scraping. |
| `docs/evidence/phase-3-6c-stripe-owner-defaults.md` | P3-6c Stripe billing owner defaults: docs-only safe defaults selecting Stripe as future provider direction while preserving mock billing default, test-mode-first rule, manual-first-pilot option, self-serve checkout disabled by default, placeholder internal plans, 14-day trial default, access matrix defaults, payment failure/refund/chargeback defaults, webhook scope defaults, config placeholder defaults, owner defaults, and remaining exact values. No Stripe SDK/API call, checkout, webhook, real billing, money movement, deployment, SMS, or live scraping. |
| `docs/evidence/phase-3-6d-stripe-webhook-verification-foundation.md` | P3-6d Stripe webhook verification foundation: adds fail-closed Stripe-Signature verifier, safe billing event normalizer, idempotency store boundary, `POST /api/v1/webhooks/stripe` route skeleton, config placeholders, staging/production boot-guard checks, and tests. No Stripe SDK/API call, checkout, billing portal, credentials, real billing, money movement, billing-state mutation, deployment, SMS, or live scraping. |
| `docs/evidence/phase-3-6e-stripe-checkout-portal-skeleton.md` | P3-6e Stripe checkout / billing portal skeleton: adds fail-closed provider boundary, config readiness helper, disabled checkout/portal provider, `POST /api/v1/billing/checkout-session`, `POST /api/v1/billing/portal-session`, config placeholders, boot-guard checks, and tests. No Stripe SDK/API call, real checkout session, real billing portal session, credentials, real billing, money movement, billing-state mutation, deployment, SMS, or live scraping. |
| `docs/evidence/phase-3-7a-deployment-ops-readiness-plan.md` | P3-7a deployment/ops readiness inspection + staging plan: documents current local-only Docker/Compose state, backend/frontend/worker/DB/Redis/secrets/observability readiness, production blockers, AWS-oriented staging architecture proposal, local/staging/production environment matrix, owner/operator values needed, P3-7b→P3-7g slice plan, and required staging smoke checks. Docs-only; no app/config/migration/env changes, AWS work, production cutover, Resend SDK/API/live adapter, Stripe, SMS, live scraping, or deployment. |
| `docs/evidence/phase-3-7b-production-dockerfile-hardening.md` | P3-7b production Dockerfile hardening: adds production-specific backend/frontend Dockerfiles, hardens backend/frontend `.dockerignore`, enables Next standalone output, records backend/frontend gate results, worker runtime strategy, Docker daemon unavailable limit, remaining deployment blockers, and safety confirmation. No deployment, AWS work, production enablement, secrets, Resend/live sending, Stripe, SMS, live scraping, provider SDK, or registry push. |
| `docs/evidence/phase-3-7b-production-docker-build-smoke.md` | P3-7b verification: starts Docker Desktop/Linux engine, verifies Docker 29.5.3, builds `automatedstructure-backend:p3-7b-prod` and `automatedstructure-frontend:p3-7b-prod`, records the minimal `frontend/package-lock.json` npm 10 sync needed for Docker `npm ci`, confirms frontend gates after the lockfile fix, and confirms no registry push, deployment, production enablement, secrets, Resend/live sending, Stripe, SMS, or live scraping. |
| `docs/STAGING_ENVIRONMENT_TEMPLATE.md` | P3-7c staging environment template: service-grouped staging config map for backend API, frontend, worker, migration task, database/RDS, Redis/rate-limit, Clerk, mock billing, Resend-disabled email, and observability; includes secret-ref naming under `/automatedstructure/staging/...`, boot-preflight rules, allowed/disallowed staging matrix, smoke checklist, and remaining owner/operator values. Template only; no real secrets or deployment. |
| `docs/evidence/phase-3-7c-staging-env-secret-template.md` | P3-7c staging environment + secret template evidence: records docs-only scope, files created/updated, staging env template summary, secret-ref naming, staging preflight/boot-guard requirements, allowed/disallowed matrix, staging smoke checklist, remaining owner/operator values, and safety confirmation. No app/config/migration/env/Dockerfile/package changes, AWS work, registry push, Resend/live sending, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-7d-cicd-release-pipeline-plan.md` | P3-7d CI/CD release pipeline plan: documents current CI state, proposed staging and production release pipelines, required backend/frontend/security checks, deployment safety gates, immutable image/artifact strategy, staging smoke evidence requirements, and remaining owner/operator values. Docs-only; no workflow implementation, deployment, registry push, AWS work, secrets, Resend/live sending, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-7d-ci-validation-gates-implementation.md` | P3-7d-impl CI validation gates: updates `.github/workflows/ci.yml` to use `npm ci`, preserve existing backend/frontend/secret-scan/pre-commit checks, add changed-file safety guards, add production backend/frontend Docker build validation with commit-SHA CI tags only, and record local gate/build/workflow-validation results. No release job, registry upload, AWS provisioning, staging/prod release, secrets, Resend/live sending, Stripe, SMS, or live scraping. |
| `docs/evidence/phase-3-demo-1-mock-send-path-readiness.md` | P3-Demo-1 mock-send-path readiness: verifies Phase 0 secure foundation + local/mock cold-outreach demo path, send gate, human review, billing/access gates, suppression/compliance, rate limits, mock provider behavior, Resend cold-outreach lockout, Stripe fail-closed billing skeleton, and production-safety status. Backend/frontend gates passed; backend/frontend production Docker builds passed with `p3-demo-1-local` tags after Docker Desktop came online. No real providers, money movement, registry push, deployment, SMS, or live scraping enabled. **Correction (P3-Demo-2):** sign-in page was a dead shell — see phase-3-demo-2. |
| `docs/evidence/phase-3-demo-2-local-mock-auth-readiness.md` | P3-Demo-2 local/mock demo login fix: stateful `MockAuthProvider` with `mockSignIn`/`mockSignOut`/localStorage; "Continue with Demo Account" button on `/login` (fail-closed in production); `TenantProvider` `X-Tenant-ID` seed from `auth.tenantId`; 14 new tests (74 frontend total). No real Clerk, no production JWT cutover, no real sending, no Stripe, no deployment, no AWS, no boot guard weakening. Frontend 74 tests PASS; backend 638 tests PASS (unchanged). |
| `docs/evidence/phase-3-7e-staging-release-runbook-plan.md` | P3-7e-plan staging release runbook: defines 20 staging prerequisites (all open), image/build procedure, migration one-off task procedure (expected head `00022_platform_admin_role`), service startup order, 21-item smoke checklist, 18 hard stop conditions, rollback plan, and 26-item evidence bundle required for real staging deploy. Docs-only; no deployment, registry push, AWS provisioning, secrets, Resend/live sending, Stripe money movement, SMS, or live scraping. |
| `docs/evidence/phase-3-7e-local-staging-rehearsal.md` | P3-7e-dryrun local staging rehearsal: fixes `frontend/Dockerfile.prod` ARG/ENV for NEXT_PUBLIC_* vars; backend 731 / frontend 141 gates PASS; both prod images built; migration head `00022_platform_admin_role` confirmed; `/health`/`/live`/`/ready` 200; browser mock login via credential form passes; Stripe checkout/portal fail-closed (503); no secrets in logs. No registry push, deployment, real providers, or AWS. Honest limits: APP_ENV=local (boot guard no-op), no Redis/Clerk/RDS/TLS. |
| `docs/evidence/phase-3-6f-prep-stripe-test-mode-smoke.md` | P3-6f-prep Stripe test-mode webhook smoke preparation: required concrete values (test secret refs, smoke approver, emergency-stop operator, Stripe CLI), required test-mode gates, 13-step internal webhook smoke scenario, 10 hard stop conditions, evidence requirements for P3-6h smoke doc, and remaining slices P3-6g through P3-6k. Docs-only; no Stripe SDK/API call, real credentials, checkout session, billing portal session, billing-state mutation, or money movement. |
| `docs/evidence/phase-3-8a-launch-readiness-dashboard.md` | P3-8a launch readiness dashboard: consolidated Phase 3 readiness for the boss — demo status (READY), completed slice summary, 38-row open blocker table with owners/values/blocking slices/risks, readiness categories (demo READY; staging/Clerk/Resend/cold outreach/Stripe test/Stripe live/production all BLOCKED), recommended next paths, risk notes, and boss-facing summary. Docs-only; no live providers, deployment, secrets, or registry push. |
| `docs/evidence/phase-3-final-boss-handoff-package.md` | P3-Final boss handoff: executive summary (14 checks), demo startup instructions and 11-step browser flow, complete-work summary (Phase 0 through P3-Audit), intentionally-not-live list with kill switches, safety gate status, open blocker summary, recommended next approval paths, boss-facing message for William. P3-Final package created at `9ec8d99`; final audited Phase 3 baseline is `747db3f`. Docs-only; no live providers, deployment, secrets, or registry push. |
| `docs/evidence/phase-3-final-requirements-architecture-audit.md` | P3-Audit final requirements and architecture compliance audit: verifies Phase 3 against locked architecture, owner decisions, safety rules, local/mock demo readiness, provider-disable constraints, CI/Docker gates, and Phase 4 planning readiness. Backend Ruff/Black/mypy/731 pytest PASS; frontend npm ci/lint/typecheck/141 tests/build PASS; backend/frontend production Docker builds PASS with `p3-audit-local` tags. Result: PASS for Phase 4 planning only. |

---

## Phase 4 evidence files (not counted among the 20 docs)

| File | Purpose |
|------|---------|
| `docs/evidence/phase-4-0-staging-pilot-entry-plan.md` | P4-0 staging and first-pilot entry evidence: records preflight, codebase/doc scan, Phase 4 scope and non-goals, required owner/operator values, proposed slices, entry/exit criteria, hard stops, files changed, and verification result. Docs-only; no deployment, AWS provisioning, registry push, provider enablement, billing money movement, SMS, or live scraping. |
| `docs/evidence/phase-4-1-staging-infrastructure-values-intake.md` | P4-1 staging infrastructure values intake and lock packet: records current staging-blocked status, required owner/operator value table using MISSING/PROPOSED/LOCKED states, proposed safe defaults, boss-facing checklist for William, locking rules, hard stops, and next-slice decision. Docs-only; no deployment, AWS provisioning, registry push, provider enablement, billing money movement, SMS, or live scraping. |
| `docs/evidence/phase-4-1b-owner-response-tracker.md` | P4-1b owner response tracker and Phase 4 decision matrix: tracks William/operator answers using MISSING/PROPOSED/LOCKED/DEFERRED states, maps decisions to allowed next slices, lists blocked slices, records safe work while blocked, and includes a boss-facing reminder. Docs-only; no deployment, AWS provisioning, registry push, provider enablement, billing money movement, SMS, or live scraping. |
| `docs/evidence/phase-4-demo-walkthrough-script.md` | P4-Demo-Walkthrough boss demo script and QA checklist: records local/mock demo objective, pre-demo setup, walkthrough steps, safety proof, troubleshooting, pass/fail QA checklist, and boss-facing close. Docs-only; no code changes, deployment, AWS provisioning, registry push, provider enablement, billing money movement, SMS, or live scraping. |
| `docs/evidence/phase-4-dependency-audit-triage-plan.md` | P4-DepAudit-Plan dependency audit triage: records npm audit summary, risk classification, safe fix strategy, proposed future fix slices, hard stops, and staging/production recommendation. Docs-only; no package updates, lockfile edits, installs, automatic fixes, deployment, provider enablement, billing money movement, SMS, or live scraping. |
| `docs/evidence/phase-4-dependency-audit-raw.json` | Raw npm audit JSON evidence for P4-DepAudit-Plan. Generated from `npm audit --json`; no package changes or automatic fixes applied. |
| `docs/evidence/phase-4-dependency-audit-fix-1.md` | P4-DepAudit-Fix-1 evidence: targeted dev/test tooling update for Vitest/Vite chain, before/after audit summary, package change rationale, full frontend gate results, remaining findings, and recommendation. |
| `docs/evidence/phase-4-dependency-audit-after-fix-1.json` | Raw npm audit JSON evidence after P4-DepAudit-Fix-1. Audit reduced 10 → 5 and critical findings reduced 1 → 0. |
| `docs/evidence/phase-4-dependency-audit-fix-2.md` | P4-DepAudit-Fix-2 evidence: records that no same-major compatible package update was available for the remaining frontend audit groups, no package files were changed, and the next path is framework upgrade planning or formal owner/security acceptance. |
| `docs/evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md` | P4-DepAudit-Fix-3-Plan evidence: owner approval and migration plan for the remaining framework dependency work. |
| `docs/evidence/phase-4-dependency-audit-next15-upgrade.md` | P4-DepAudit-Fix-3a evidence: records William's local-only approval, the controlled `next@15.5.16` / `eslint-config-next@15.5.16` attempt, package/version observations, before/after audit summary, frontend/backend gate results, Docker/browser-smoke limitations, rollback, remaining blockers, and final BLOCKED verdict. |
| `docs/evidence/phase-4-dependency-audit-after-next15.json` | Raw npm audit JSON evidence after the attempted Next 15.5.16 upgrade. Audit improved 5 → 2 but still reported 1 high Next finding and 1 moderate nested PostCSS finding, so the dependency blocker remains open. |
| `docs/evidence/phase-4-dependency-audit-next15-retry.md` | P4-DepAudit-Fix-3a-Retry evidence: records revised patched Next 15 target selection, `15.5.18` and `15.5.19` attempts, package/version observations, frontend/backend gate results, remaining moderate nested PostCSS findings, Docker lockfile-sync failure, rollback, remaining blockers, and final BLOCKED verdict. |
| `docs/evidence/phase-4-dependency-audit-after-next15-retry.json` | Raw npm audit JSON evidence after the patched Next 15 retry. High findings cleared, but audit still reported 2 moderate findings through nested PostCSS under Next, so the dependency blocker remains open. |
| `docs/evidence/phase-4-dependency-audit-lockfile-investigation.md` | P4-DepAudit-Fix-3a-Lockfile-Investigation evidence: records Option 2 dependency investigation, local npm vs Docker npm observations, nested PostCSS root cause, targeted override experiments, Docker lockfile failure, gate results, rollback, remaining blockers, and final BLOCKED verdict. |
| `docs/evidence/phase-4-dependency-audit-after-lockfile-investigation.json` | Raw npm audit JSON evidence for the experimental scoped override state. It reports 0 vulnerabilities locally, but the package changes were not retained because Docker production build still failed at `npm ci`. |
| `docs/evidence/phase-4-dependency-audit-npm-docker-align.md` | P4-DepAudit-Fix-3a-NpmDockerAlign evidence: records package-manager alignment, Docker npm 10 lockfile regeneration, retained Next 15.5.19 package changes, narrow PostCSS override, audit/backend/frontend/Docker/smoke gate results, remaining launch blockers, and final COMPLETE verdict. |
| `docs/evidence/phase-4-dependency-audit-after-npm-docker-align.json` | Raw npm audit JSON evidence after the Docker npm-aligned Next 15 lockfile fix. Reports 0 vulnerabilities in the retained branch state. |
| `docs/evidence/phase-4-next15-branch-review-summary.md` | P4-DepAudit-Next15-PR-Review evidence: owner-review summary for the Next 15 dependency-fix branch, including branch/commit, retained package changes, non-changes, gate evidence, remaining limitations, and merge recommendation. |
| `docs/evidence/phase-4-first-pilot-readiness-checklist.md` | P4-FirstPilot-Readiness evidence: first paying-client pilot checklist covering scope, required pre-client gates, onboarding fields, demo-to-pilot gaps, go/no-go criteria, hard stops, and approvals. |
| `docs/evidence/phase-4-monitoring-alerts-incident-plan.md` | P4-Monitoring-Alerts-Plan evidence: staging/pilot monitoring scope, alert categories, required owners, severity levels, smoke observability, rollback plan, hard stops, and William-facing questions. |
| `docs/evidence/phase-4-local-readiness-closeout.md` | P4-LocalReadiness-Closeout evidence: final local/demo readiness closeout package resumed after a partial attempt, including William's pause decision, backend/frontend gate evidence, known master audit blocker, incomplete Docker compose evidence, route smoke result, demo readiness, blocked list, and recommendation. |
| `docs/evidence/phase-4-sendgate-compliance-qa.md` | P4-LocalReadiness-Closeout send-gate/compliance QA evidence: records local/mock send-gate, billing/access, compliance, webhook fail-closed, provider-boundary, and server-side trust test coverage and remaining risks. |
| `docs/evidence/phase-4-first-client-onboarding-runbook.md` | P4-LocalReadiness-Closeout first-client onboarding runbook: preparation-only checklist for tenant intake, billing/access, compliance, suppression, sending policy, pilot go/no-go, evidence bundle, and William approval boundaries. |
| `docs/evidence/phase-4-local-e2e-completion.md` | P4-LocalE2E-Completion evidence: local-only E2E audit covering backend/frontend/API route inventory, flow matrix, gate results, local route smoke, Docker daemon blocker, master audit blocker, safety confirmation, and recommendation. |
| `docs/evidence/phase-4-local-docker-e2e-retry.md` | P4-LocalDockerE2E-Retry evidence: Docker Desktop/Linux environment, compose build/start result, service status, backend health/readiness, frontend route smoke, local mock auth smoke, backend campaign-create 500 blocker, safety confirmation, remaining blockers, and recommendation. |
| `docs/evidence/phase-4-local-docker-e2e-fix-1-campaign-create.md` | P4-LocalDockerE2E-Fix-1-CampaignCreate evidence: campaign-create 500 root cause, campaign/idempotency repository row-mapping fixes, regression tests, backend/frontend/Docker gate results, campaign create/list verification, remaining contact import blocker, safety confirmation, and recommendation. |
| `docs/evidence/phase-4-local-docker-e2e-fix-2-contact-import.md` | P4-LocalDockerE2E-Fix-2-ContactImport evidence: contact import 500 root cause, contact/import-row repository row-mapping fixes, regression test, repository scalar-mapping audit, backend/frontend/Docker gate results, contact import/list verification, campaign-contact selection, remaining draft generation blocker, safety confirmation, and recommendation. |
| `docs/evidence/phase-4-local-docker-e2e-fix-3-draft-generation.md` | P4-LocalDockerE2E-Fix-3-DraftGeneration evidence: draft generation 500 root cause, draft/evidence/safety/review repository row-mapping fixes, regression tests, repository scalar-mapping audit, backend/frontend/Docker gate results, draft generation/evidence verification, groundedness fail-closed caveat, safety confirmation, and recommendation. |
| `docs/evidence/phase-4-local-docker-e2e-fix-4-grounded-happy-path-seed.md` | P4-LocalDockerE2E-Fix-4-GroundedHappyPathSeed evidence: needs_regeneration root cause (missing grounding data + newly-discovered sending/audit repository row-mapping bugs), local/mock grounding seed design and safety rationale, tests added, backend/frontend/Docker gate results, full review/send-gate/mock-send/audit E2E verification, safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-repository-row-mapping-hardening.md` | P4-RepositoryRowMapping-Hardening evidence: repo-wide scan summary (9 files fixed, 2 confirmed safe, 2 confirmed dead code), auth-path and research-worker crash findings, fix summary, regression tests added, backend/frontend/Docker gate results, live Postgres spot-checks, safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-final-manual-demo-smoke.md` | P4-FinalManualDemoSmoke evidence: final local Docker demo smoke covering the core demo surface, billing/access, compliance/suppression, deliverability/outcomes, safety confirmation, and the logout -> login local mock auth blocker later fixed by P4-LocalMockAuthSessionCycle-Fix. |
| `docs/evidence/phase-4-local-mock-auth-session-cycle-fix.md` | P4-LocalMockAuthSessionCycle-Fix evidence: local/mock logout -> re-login root cause and fix, per-login demo-token behavior, revoked-session preservation, production-auth safety proof, tests, gate results, Docker health/readiness, auth-cycle verification, abbreviated demo smoke, safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-fresh-volume-bootstrap.md` | P4-FreshVolumeBootstrap evidence: fresh-volume tenant-bootstrap gap and root cause, `bootstrap_local_demo.py` design and repository additions, idempotency/RLS safety rationale, tests added, backend/frontend gate results, isolated fresh-volume Docker verification (migrate -> bootstrap -> grounding seed -> full happy-path E2E), safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-local-e2e-smoke-script.md` | P4-LocalE2E-SmokeScript evidence: repeatable local Docker E2E smoke script, bootstrap identity-provider drift fix, idempotency replay recovery behavior, tests added/updated, backend/frontend gates, Docker health/readiness, 5 consecutive smoke passes against the normal dev volume, safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-local-load-stability-smoke.md` | P4-LocalLoadStabilitySmoke evidence: local-only stability smoke command, local/demo guards, request/iteration counts, health/auth/E2E/outbound/audit coverage, tests added, backend/frontend/Docker gate results, stability result counts, safety confirmation, and remaining blockers. |
| `docs/demo/BOSS_CLIENT_DEMO_PACKET.md` | P4-BossClientDemoPacket: plain-English boss/client demo and first-client readiness handoff covering AutomatedStructure summary, readiness statuses, demo script, talking points, evidence summary, intentionally blocked live capabilities, William approvals, first-client checklist, next decisions, and safe local commands. |
| `docs/evidence/phase-4-final-local-polish.md` | P4-FinalLocalPolish evidence: final local Docker rehearsal, health/readiness, local E2E/stability results, demo route smoke, docs typo scan, dead-code cleanup of `AuditRepository.list_recent()`, gate results, UI polish status, safety confirmation, and remaining blockers. |
| `docs/evidence/phase-4-rls-defense-in-depth-fix.md` | P4-RLSDefenseInDepth-Fix evidence: bug/gap summary for the RLS-only `tenant_repo.py`/`audit/repository.py` read/update paths, explicit-filter fix summary, deferred non-live-risk follow-ups, TDD tests added, backend/frontend gate results, Docker/E2E/stability results, safety confirmation, and remaining blockers. |

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
| First-paying-client production billing | P3-6a packet, P3-6b readiness contract, P3-6c safe defaults, P3-6d webhook foundation, and P3-6e checkout/portal skeleton created; still needs final values, named owners, test refs/price IDs, smoke approval, real session creation approval, billing-state mutation design, and live-mode approval before implementation | First paying client | BILLING / ADR_BILLING |

## Launch blockers (from §25) — mirrored in `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`

Legal review (compliance) · Clerk production configuration + platform-admin MFA (auth) · centralized mock billing gates (billing) · rate limits/abuse (security) · credential encryption + AWS Secrets Manager/KMS (security) · RLS/object-auth tests (security) · backup restore drill (devops) · in-product observability + LangSmith faithfulness logging (SRE/AI) · privacy export/delete/vector purge (privacy) · production boot guard missing (security/ops).

---

## Conflicts / gaps

- **Conflicts:** None at product/architecture level (Appendix A). If older source files disagree, this guide wins unless stricter legal/provider/incident rule.
- **Open owner decisions:** limited to genuinely unresolved launch/future items above; Clerk, US compliance baseline, AWS Secrets Manager/KMS, and mock-only MVP billing are owner-confirmed.
- **Gaps:** none beyond the listed owner decisions. No requirements invented.
