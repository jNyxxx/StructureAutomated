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
