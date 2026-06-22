# Testing & Audit

**Purpose:** Required test suites, audit/evidence requirements, phase completion gates, completion-report template, and review/audit rules. **Documentation only — defines what must be proven, not the tests themselves.**
**Source sections:** Master guide §23 (testing/completion gates), §7 (DB acceptance), §8 (isolation tests), §25 (launch evidence bundle).
**Status:** Draft
**Related docs:** [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (acceptance checklist) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) (isolation tests) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (send-gate tests) · [AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md) (evals) · [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md) (CI) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)

---

## 1. Required test suites

| Suite | Coverage |
|---|---|
| Unit | Services, validators, gates, throttling, state machines. |
| API | Auth, permissions, schemas, errors, rate limits. |
| RLS | Cross-tenant denial for **every** tenant table. |
| Object auth | UUID guessing + role denial for every protected object family (IDOR). |
| Worker | Tenant context, retries, DLQ, idempotency, billing re-checks. |
| Billing | Subscription states + route/service/worker locks. |
| Webhook | Signature, duplicate, replay, bad payload, async processing. |
| Import | File limits, invalid rows, duplicates, formula injection, suppression. |
| Agent | Prompt injection, groundedness, tool permissions, cost caps. |
| Send | No duplicate sends, rate limits, warm-up, suppression, paused mailbox. |
| Frontend | Protected routes, form validation, role UI, states. |
| E2E demo | Import → campaign → draft → review → mock send → outcomes. |

Per-domain detail: DB invariants → [DATABASE_SCHEMA §9](DATABASE_SCHEMA.md); tenant isolation → [AUTH_AND_RBAC §8](AUTH_AND_RBAC.md); send gate → [EMAIL_COMPLIANCE_AND_SEND_GATE §9](EMAIL_COMPLIANCE_AND_SEND_GATE.md); AI evals → [AI_SAFETY_AND_GROUNDEDNESS §9](AI_SAFETY_AND_GROUNDEDNESS.md). Privacy/delete/export + deployment checks: see §2 below and [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md).

## 2. Audit & evidence requirements

Launch evidence bundle (attach to completion report):

- [ ] Empty-DB migration proof · RLS isolation output · auth/session report · RBAC/object-auth negative tests.
- [ ] Mock billing state transitions + centralized gate proof.
- [ ] Queue retry/crash/DLQ/duplicate-send prevention tests.
- [ ] Send-gate dry-run + worker tests for **each** no-send reason.
- [ ] DNS/warm-up/throttle/pause-threshold tests.
- [ ] LangSmith traces + faithfulness logs · groundedness reports · prompt-injection evals.
- [ ] Export/delete/vector-purge + retention job proof.
- [ ] Backup restore drill report.
- [ ] In-product observability evidence + LangSmith faithfulness logging. External Slack/internal alerts are post-demo.
- [ ] Secret scan · dependency scan · SAST · webhook verification · rate-limit tests.
- [ ] Counsel-approved privacy/terms/outreach/unsubscribe/data-use language.
- [ ] Staging E2E run with screenshots, logs, traces, owner sign-off.

Full launch control + go/no-go → [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md).

## 3. Phase completion gates

**Phase 0 complete only when:**
- [ ] Required repo docs + ADRs exist.
- [ ] Migrations run from empty DB.
- [ ] Forced RLS enabled and tested.
- [ ] Auth/session tests pass.
- [ ] RBAC/object-authorization tests pass.
- [ ] Billing gate skeleton works in routes and workers.
- [ ] Queue/idempotency tests pass.
- [ ] Compliance profile + suppression baseline exist.
- [ ] Structured logs + audit events exist.
- [ ] CI blocks secrets, failing tests, migration drift.

**Phase 1 complete only when:**
- [ ] CRE demo tenant seeded.
- [ ] CSV import validates, normalizes, dedupes, audits rows.
- [ ] LangGraph cold-outreach run works in mock mode.
- [ ] Research snippets + RAG context tenant-scoped.
- [ ] Drafts grounded + injection-fenced; human edits force re-grounding.
- [ ] Review queue works.
- [ ] Send gate blocks and explains unsafe sends.
- [ ] Mailbox pool/warm-up/throttle real with mock send adapter.
- [ ] Mock sends/outcomes idempotent.
- [ ] Deliverability + outcomes dashboards show useful demo data.
- [ ] E2E proves no cross-tenant leak and no duplicate send.
- [ ] Completion report filed.

## 4. Completion report template

Every phase/component report must include: scope implemented · commands run · test results · RLS proof · auth/RBAC proof · billing-gate proof (if applicable) · agent trace links (if applicable) · known issues · launch blockers remaining · frontend screenshots/rendered evidence (if applicable) · final score.

## 5. Review/audit rules (docs + future implementation)

- A table/feature is **not accepted** until tests, traces, logs, docs, and a completion report exist (CLAUDE rule 15).
- Docs reviewed for: duplication, bloat, missing source links, contradictions, missing blockers/owner-decisions, missing RLS/security/billing/send-gate/AI-safety rules, invented requirements.
- Implementation audited against: forced RLS + tenant isolation, object auth, billing locks (routes + workers), idempotency/no-duplicate-send, send-gate non-bypass, AI safety gates, privacy export/delete/purge, secret hygiene.
- Any missing/ambiguous item → **"Needs owner decision"**, never guessed.
