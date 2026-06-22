# Launch Blockers & Owner Decisions

**Purpose:** Single launch-control checklist — current verdict, blockers, owner decisions, go/no-go, pilot constraints, and unresolved items, bucketed by when they must be resolved. No decisions invented; unresolved items marked.
**Source sections:** Master guide §25 (production readiness / launch control), Appendix A (conflict check).
**Status:** Draft
**Related docs:** [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) (evidence bundle, gates) · [PHASE_0_1_IMPLEMENTATION_PLAN](PHASE_0_1_IMPLEMENTATION_PLAN.md) · the 4 ADRs · all domain docs

---

## 1. Current verdict

Implementation-ready for **Phase 0 + Phase 1**, **not** production launch approval. Readiness **6/10** until implementation evidence exists. Controlled pilot requires **avg ≥ 8.0/10**, **no critical category < 8/10**, **no open Critical/High blocker**, and a **signed evidence bundle**.

## 2. Resolution buckets

### A. Must DECIDE before coding
| Decision | Recommended default | Authority |
|---|---|---|
| Auth provider | Managed auth (fastest production-safe MVP); first-party only with full security lifecycle | [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) |
| Queue transport | Postgres durable jobs + SQS production dispatch | [ADR_QUEUE_TRANSPORT](ADRs/ADR_QUEUE_TRANSPORT.md) |
| Billing access-state defaults | Trial 14d · grace 7d · past-due read-only+billing · chargeback immediate lock | [ADR_BILLING_ACCESS_STATES](ADRs/ADR_BILLING_ACCESS_STATES.md) |

### B. Must COMPLETE before external users
Legal review (compliance) · refresh rotation + session revocation · **platform-admin MFA** · billing state machine + Stripe webhooks · rate limits/abuse protection · credential encryption + Secrets Manager · RLS/object-auth tests · backup restore drill · observability alerts · privacy export/delete/vector purge · production boot guard · **target market + compliance baseline locked** ([ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md)) · focused repo docs · support-access approval flow · production mock-provider exception policy (default: no exception).

### C. Must NEVER postpone (NO-GO if violated)
Tenant isolation holds · send gate cannot be bypassed · idempotency prevents duplicate sends/billing events · live webhooks rejected without verification · billing state cannot grant paid access incorrectly · agent cannot directly send / access secrets / bypass tool permissions · backup restore drill exists and passes.

### D. Safe to BUILD now
All Phase 0 + Phase 1 scope in mock mode ([PHASE_0_1_IMPLEMENTATION_PLAN](PHASE_0_1_IMPLEMENTATION_PLAN.md)) — foundation, isolation, gates, CRE demo, mock sends/outcomes. No live sending, SMS, ads, or live scraping.

## 3. Launch blockers

| Blocker | Area | Required fix |
|---|---|---|
| Legal review for SMS/cold outreach/privacy claims | Compliance | Counsel-approved policies + UI copy |
| Refresh rotation + session revocation | Auth | Session table, rotation, revocation, reuse detection |
| MFA for platform admins | Auth | Enforce MFA for platform super/support admins before external users / production; strongly recommended for tenant owners/admins |
| Billing state machine + Stripe webhooks | Billing | Lifecycle, verification, reconciliation, access gates |
| Rate limits + abuse protection | Security | App/WAF/Redis/provider limits |
| Credential encryption + Secrets Manager | Security | KMS/Secrets Manager integration |
| RLS/object-auth tests | Security | Automated tenant + object tests |
| Backup restore drill | DevOps | Successful restore test + report |
| Observability alerts | SRE | CloudWatch/Sentry/LangSmith alerts |
| Privacy export/delete/vector purge | Privacy | Working workflows + policy-aligned retention |
| Auth provider not locked | Auth | Complete [ADR_AUTH_PROVIDER](ADRs/ADR_AUTH_PROVIDER.md) before auth |
| Compliance jurisdiction not locked | Compliance | Define market, baseline, sender identity, unsubscribe, retention before live sending |
| Production boot guard missing | Security/Ops | Startup checks fail unsafe prod/staging config |
| Focused repo docs missing | Engineering | Generate component docs before coding those areas |

## 4. Owner decisions (with defaults + needed-by)

| Decision | Recommended default | Needed by |
|---|---|---|
| Trial duration | 14 days | Billing launch |
| Grace period | 7 days | Billing launch |
| Refund/chargeback policy | Manual refund review; immediate chargeback lock | Billing launch |
| Past-due access | Read-only + billing access after lock | Billing launch |
| SMS legal wording | Counsel-approved only | Phase 3 |
| CRE research source approval | Public/mock for MVP; legal review before live scraping | Live research |
| Support access approval | Owner/super-admin grant + audit | External users |
| Auth provider | Managed auth; first-party only with full lifecycle | Before auth coding |
| Target recipient market | US CRE / Philippines / mixed-global / other | Before live sending |
| Compliance baseline | Counsel-approved baseline for chosen market | Before live sending |
| Production mock-provider exception | No exception by default | Before any prod demo on mock providers |
| Add ADRs for mock/live adapter pattern + privacy retention defaults? | Keep the 20-file set locked; do not add the two ADRs unless later implementation proves they are needed | Doc-set governance — revisit during implementation |

> All recommended defaults are **defaults, not final decisions**. Items remain **unresolved** until the owner confirms in writing.

## 5. Required ≥8/10 categories (external production)

Product scope · multi-tenant isolation · auth/sessions/support · authorization/object permissions · billing enforcement · queue/workers/idempotency · cold-email compliance + send gate · deliverability/mailbox ops · AI safety/groundedness/tool permissions · privacy/retention/data rights · secrets/credential security · observability/incident response · DevOps/deploy/backup/rollback · testing/staging proof · legal/provider approvals.

## 6. Go / No-Go

**GO only when:** avg readiness ≥ 8.0/10 · every critical category ≥ 8/10 · no open Critical/High blocker · staging E2E accepted · legal/security/backup/billing evidence attached · owner accepts remaining Medium/Low risks in writing.

**NO-GO if any:** tenant isolation test fails · send-gate bypass exists · idempotency allows duplicate sends/billing events · live webhook accepted without verification · billing state grants paid access incorrectly · agent can send/access secrets/bypass tool permissions · backup restore drill fails or missing · Critical/High security/legal issue remains.

## 7. Pilot production policy

Assisted onboarding only · 1–2 friendly pilot tenants · **manual approval for all live outbound** · conservative mailbox caps · no SMS/ads/GBP/advanced-CRM/auto signal-triggered live sends · live research only from approved sources · daily monitoring (sends, bounces, replies, complaints, costs, agent failures, blocked-send reasons) · weekly launch review until platform holds ≥8/10 for **30 consecutive days**.

## 8. Conflicts

Per Appendix A, **no product/architecture conflicts** across source files. This guide wins over older sources unless stricter signed legal policy, provider terms, or production-incident decisions apply. Evidence bundle checklist lives in [TESTING_AND_AUDIT §2](TESTING_AND_AUDIT.md).
