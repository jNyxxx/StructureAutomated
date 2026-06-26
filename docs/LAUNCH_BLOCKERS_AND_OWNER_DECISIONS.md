# Launch Blockers & Owner Decisions

**Purpose:** Single launch-control checklist - current verdict, blockers, owner decisions, go/no-go, pilot constraints, and unresolved items, bucketed by when they must be resolved. No decisions invented; unresolved items marked.
**Source sections:** Master guide §25 (production readiness / launch control), Appendix A (conflict check).
**Status:** Draft
**Related docs:** [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (evidence bundle, gates) - [PHASE_0_1_IMPLEMENTATION_PLAN](PHASE_0_1_IMPLEMENTATION_PLAN.md) - the 4 ADRs - all domain docs

---

## 1. Current verdict

Implementation-ready for **Phase 0 + Phase 1**, **not** production launch approval. Readiness **6/10** until implementation evidence exists. Controlled pilot requires **avg >= 8.0/10**, **no critical category < 8/10**, **no open Critical/High blocker**, and a **signed evidence bundle**.

P3-1 read-only production-readiness audit (2026-06-26): ready to begin the first prod-hardening slice, **zero true blockers**, all stop-gates hold — see [evidence/phase-3-1-production-readiness-audit.md](evidence/phase-3-1-production-readiness-audit.md). No production / real providers / sending / Stripe / SMS enabled; no app code changed.

P3-1a first hardening slice (2026-06-26): boot-guard tenant-owned RLS coverage expanded 2→**29** tables (count corrected 23→29 with evidence) and `controlled_demo` owner-approval attestation added (fails closed) — both §6 rows resolved; see [evidence/phase-3-1a-boot-guard-hardening.md](evidence/phase-3-1a-boot-guard-hardening.md). Backend 525 / frontend 122 gates PASS. No production / providers / sending / Stripe / SMS / migrations enabled.

## 2. Resolved owner decisions

| Decision | Final owner decision | Authority |
|---|---|---|
| Auth provider | Clerk managed auth | [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) |
| Compliance baseline | United States MVP baseline; first target market = US | [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) |
| Production secrets | AWS Secrets Manager + AWS KMS | [CLAUDE](../CLAUDE.md), [PHASE_0_1_IMPLEMENTATION_PLAN](PHASE_0_1_IMPLEMENTATION_PLAN.md) |
| MVP billing | Mock-only billing states, schema, tenant status, central gates, deterministic tests | [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md) |
| Billing states | `trialing`, `active`, `past_due`, `canceled`, `unpaid`, `inactive` | [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) |
| First real client sending | Manual human approval for every AI-generated cold-email draft | [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) |
| Contact/research deletion | Soft-delete first, hard-delete after 30 days, retain minimum hashed suppression data | [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md) |
| Observability MVP | In-product observability + LangSmith faithfulness logging; Slack/internal alerts post-demo | [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md) |
| Phase 3 entry (planning) | Owner approved entering Phase 3 (Production-Readiness & Real-Provider Enablement program); scope locked to P3-0…P3-7. No real sending / Stripe / SMS / provider integration / live-scraping / production-deploy work without explicit per-slice owner approval recorded here. | [PHASE_3_IMPLEMENTATION_PLAN](PHASE_3_IMPLEMENTATION_PLAN.md) (owner approval 2026-06-26) |

## 3. Must COMPLETE before external users

Legal review for live cold outreach/privacy claims - Clerk production configuration and platform-admin MFA - app-side tenant/RBAC/object-auth/session invalidation - centralized mock billing gates - rate limits/abuse protection - AWS Secrets Manager/KMS secret handling - RLS/object-auth tests - backup restore drill - in-product observability + LangSmith traces - privacy export/delete/vector purge - production boot guard - support-access approval flow - production mock-provider exception policy (default: no exception).

## 4. Must NEVER postpone (NO-GO if violated)

Tenant isolation holds - send gate cannot be bypassed - idempotency prevents duplicate sends/billing events - billing state cannot grant paid access incorrectly - agent cannot directly send / access secrets / bypass tool permissions - secrets never leak to logs/audit/prompts/exports/client responses - backup restore drill exists and passes.

## 5. Safe to BUILD now

All Phase 0 + Phase 1 scope in mock mode ([PHASE_0_1_IMPLEMENTATION_PLAN](PHASE_0_1_IMPLEMENTATION_PLAN.md)) - foundation, isolation, gates, CRE demo, mock sends/outcomes. No live sending, SMS, ads, live scraping, Slack/internal alerts, or real Stripe.

## 6. Launch blockers

| Blocker | Area | Required fix |
|---|---|---|
| Legal review for live cold outreach/privacy claims | Compliance | Counsel-approved policies + UI copy before live sending |
| Clerk production configuration + platform-admin MFA | Auth | Verify Clerk settings, domains, templates, and MFA before external users / production |
| App-side tenant authorization | Auth/RBAC | Tenant membership, RBAC, object auth, support access, audit, tenant context, and RLS tests |
| Centralized billing gates | Billing | `is_active(tenant)` + `has_feature(tenant, key)` with route/worker tests |
| Rate limits + abuse protection | Security | App/WAF/Redis/provider limits |
| Credential encryption + Secrets Manager | Security | AWS Secrets Manager + AWS KMS integration |
| RLS/object-auth tests | Security | Automated tenant + object tests |
| Backup restore drill | DevOps | Successful restore test + report |
| In-product observability + LangSmith logging | SRE/AI | Demo observability and faithfulness traces |
| Privacy export/delete/vector purge | Privacy | Working workflows + policy-aligned retention |
| Production boot guard missing | Security/Ops | Startup checks fail unsafe prod/staging config |
| ~~Boot-guard RLS coverage (2 of 23 tenant tables)~~ **RESOLVED (P3-1a)** | Security/Ops | Boot guard now runtime-verifies ENABLE+FORCE RLS on all **29** tenant-owned tables (audit_events documented exception); count corrected 23→29 with evidence; drift-proof + fake-conn tests added. See [evidence/phase-3-1a-boot-guard-hardening.md](evidence/phase-3-1a-boot-guard-hardening.md) |
| ~~controlled_demo lacks owner-approval attestation~~ **RESOLVED (P3-1a)** | Security/Ops | `controlled_demo_approved_by` attestation added; boot guard fails closed in production when `controlled_demo` is set without a recorded approver. Still no reachable live-provider path. See [evidence/phase-3-1a-boot-guard-hardening.md](evidence/phase-3-1a-boot-guard-hardening.md) |

## 7. Remaining owner decisions

| Decision | Default/current position | Needed by |
|---|---|---|
| Counsel-approved privacy/terms/outreach/unsubscribe/data-use language | Required before live sending | Live sending |
| CRE research source approval | Public/mock for MVP; legal review before live scraping/paid research | Live research |
| Support access approval operations | Owner/super-admin grant + audit | External users |
| Production mock-provider exception | No exception by default | Before any prod demo on mock providers |
| First-paying-client production billing | Stripe products/prices, plan entitlements, webhook/dunning rollout | First paying client |
| SMS legal wording | Counsel-approved only | Phase 3 |

## 8. Required >=8/10 categories (external production)

Product scope - multi-tenant isolation - auth/sessions/support - authorization/object permissions - billing enforcement - queue/workers/idempotency - cold-email compliance + send gate - deliverability/mailbox ops - AI safety/groundedness/tool permissions - privacy/retention/data rights - secrets/credential security - observability/incident response - DevOps/deploy/backup/rollback - testing/staging proof - legal/provider approvals.

## 9. Go / No-Go

**GO only when:** avg readiness >= 8.0/10 - every critical category >= 8/10 - no open Critical/High blocker - staging E2E accepted - legal/security/backup/billing evidence attached - owner accepts remaining Medium/Low risks in writing.

**NO-GO if any:** tenant isolation test fails - send-gate bypass exists - idempotency allows duplicate sends/billing events - billing state grants paid access incorrectly - agent can send/access secrets/bypass tool permissions - backup restore drill fails or missing - Critical/High security/legal issue remains.

## 10. Pilot production policy

Assisted onboarding only - 1-2 friendly pilot tenants - **manual approval for every AI-generated cold-email draft for the first real client** - conservative mailbox caps - no SMS/ads/GBP/advanced-CRM/auto signal-triggered live sends - live research only from approved sources - daily monitoring (sends, bounces, replies, complaints, costs, agent failures, blocked-send reasons) - weekly launch review until platform holds >=8/10 for **30 consecutive days**.

## 11. Conflicts

Per Appendix A, **no product/architecture conflicts** across source files. This guide wins over older sources unless stricter signed legal policy, provider terms, or production-incident decisions apply. Evidence bundle checklist lives in [TESTING_AND_AUDIT §2](TESTING_AND_AUDIT.md).
