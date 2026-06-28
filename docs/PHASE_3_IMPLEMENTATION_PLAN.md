# Phase 3 Implementation Plan

**Purpose:** Lock the scope of Phase 3 after owner approval to enter Phase 3 planning, and break it into safe, ordered slices (P3-0…P3-7) with classification, acceptance criteria, and stop gates. This is the Phase 3 analog of `PHASE_0_1_IMPLEMENTATION_PLAN.md`. It is a planning artifact, **not** one of the locked 20 implementation docs.
**Source sections:** Master guide §1, §24, §25, §26; `PHASE_0_1_IMPLEMENTATION_PLAN.md` §6 (forward roadmap); `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`.
**Status:** Accepted draft (scope lock). Risky slices (P3-3, P3-5, P3-6, P3-7) remain **Owner decision needed** until per-slice approval is recorded.
**Related docs:** [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md) · [ARCHITECTURE](ARCHITECTURE.md) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) · [evidence/phase-2-exit-completion](evidence/phase-2-exit-completion.md)

---

## 1. Owner approval (P3-0)

Owner approved **entering Phase 3 (planning)** on 2026-06-26. Recorded in
`LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` §2 (Resolved owner decisions).

Approval covers **scope lock + planning only**. It does **not** approve real sending, Stripe,
SMS, OAuth/provider integration, live scraping, or production deployment. Each risky slice
requires its own written owner approval recorded in the launch-blockers register before work
starts.

## 2. Phase 3 definition + scope reconciliation

The forward roadmap (`PHASE_0_1_IMPLEMENTATION_PLAN.md` §6) defines Phase 3 narrowly:

> `| 3 | Email/SMS campaigns | Opted-in drips, SMS consent/compliance, Twilio. Legal launch blocker. |`

The owner-approved program here is **broader** — a **Production-Readiness & Real-Provider
Enablement** program. The roadmap's email/SMS feature maps to **P3-4** (design) + **P3-5** (real
sending, incl. Twilio/SMS, gated). This is a deliberate framing, surfaced for owner confirmation,
not a silent redefinition.

**Owner-confirm item:** confirm Phase 3 = the broad production-readiness program below (default),
vs. strictly the roadmap's email/SMS feature.

## 3. Verified current ground truth (2026-06-26)

- DB migrations exist: 21 files `0001_extensions` → `00021_outcomes` (head `00021_outcomes`). Live DB smoke needs provisioning + `alembic upgrade head` + seed, **not** new migrations.
- Production boot guard exists: `backend/app/observability/boot_guard.py` (`enforce_config` → `config_failures` + `database_failures`) — the authoritative production-readiness gate.
- Safety UI exists and is pervasive: `frontend/components/states/local-mock-notice.tsx`, `frontend/components/badges/gate-reason-badge.tsx`.
- CI exists (`.github/workflows/ci.yml`); `docker-compose.yml` exists; worker stubs exist but are non-functional; `docs/ADRs/ADR_QUEUE_TRANSPORT.md` exists.
- Test posture: 515 backend pytest, 122 frontend vitest green (P2-exit). No live DB smoke, no browser e2e harness.

## 4. Slice plan (order, class, acceptance / stop gate)

Classes: **planning** · **local/mock hardening** · **production readiness** · **real provider integration** · **deferred/not approved**.

| Slice | Goal | Class | Acceptance / stop gate |
|---|---|---|---|
| **P3-0** | Approval capture + scope lock | planning | This doc + register row committed. (done by this slice) |
| **P3-1** | Production-readiness audit + launch-blockers refresh | production readiness (audit, docs) | Read-only. Confirm migration head `00021`; verify RLS **enabled + forced** on **all** tenant-owned tables (not just `tenants`/`tenant_memberships`); CI green; enumerate the boot-guard conditions as a checklist with current status; refresh §6 launch-blockers. No code changes. |
| **P3-2** | Live DB smoke + seeded demo env | local/mock hardening + production readiness | Postgres via `docker-compose`; `alembic upgrade head`; least-privilege app-role (`NOSUPERUSER`, no `BYPASSRLS`); seed a demo tenant; **live RLS isolation test** (query tenant A under tenant B context → empty); duplicate-send prevention + send-gate **dry-run** against the real DB; `/ready` reports `migrations: up_to_date`. No providers, no production, no real sending. |
| **P3-3** | Auth / Clerk production readiness | production readiness | **Owner decision needed** (Clerk prod config + keys). Real JWKS verification, session revocation, MFA position; keep `local_mock` auth for non-prod. Behind config; no production cutover in this slice. |
| **P3-4** | Provider-integration **design** (no implementation) | production readiness (design) | Adapter contracts/design only for mailbox (SES/SendGrid), Twilio SMS, Stripe, DNS verifier. Zero real network calls, zero credentials. |
| **P3-5** | Real sending / provider integration | real provider integration — **DEFERRED** | **STOP GATE.** P3-5a→P3-5d docs-only design/packet done; **P3-5b** shipped the fail-closed provider boundary (mock adapter only); **P3-5e** recorded owner approval — **provider = Resend**, subdomain/sender/footer/first-pilot caps/webhook scope/ownership recorded, real sending still disabled, adapter not built. Future real-adapter slices **P3-5f→P3-5h** gated on the 8 concrete pre-smoke values (secret refs, DNS verification, monitored Reply-To, mailing details, internal recipient, emergency-stop + deliverability owner names) + counsel-approved legal copy. External sending (P3-5i) needs separate approval + green internal-smoke evidence. No live adapter, provider credentials, provider calls, or deployment until recorded. See [evidence/phase-3-5e-owner-approval-resend-roadmap.md](evidence/phase-3-5e-owner-approval-resend-roadmap.md). |
| **P3-6** | Stripe / payment | real provider integration — **DEFERRED** | **STOP GATE.** Requires written owner approval **and**: first-paying-client billing decision (products/prices/entitlements/webhooks/dunning). Not started until recorded. |
| **P3-7** | Deployment runbook + staging | production readiness | Staging provisioning, AWS Secrets Manager + KMS wiring, backup/restore drill + RPO/RTO, go/no-go. **All boot-guard conditions must pass before any production boot.** |

Suggested execution order: P3-1 → P3-2 → P3-4 (done as rate-limit/abuse-protection hardening) → P3-5a–P3-5e docs-only provider-lane design + owner approval (Resend selected) → P3-3 frontend Clerk when owner values are available → P3-7, with P3-5f→P3-5h real-adapter work (and P3-6) only after their stop gates clear.

## 5. Required owner decisions before risky work

| Decision | Blocks | Register status |
|---|---|---|
| Real-sending approval | P3-5 | **Pilot lane approved** (P3-5e 2026-06-28) — provider/domain/caps/webhook/ownership recorded; live sending still disabled; full live-send approval still gated on legal copy + 8 concrete pre-smoke values |
| Email provider choice | P3-5 | **Resolved** — **Resend** (P3-5e 2026-06-28) |
| SMS provider choice | P3-5 | Open |
| Stripe / payment approval | P3-6 | Open ("First-paying-client production billing", Needed by: first paying client) |
| SMS approval + **SMS legal wording** | P3-4/P3-5 | Open ("SMS legal wording", Needed by: Phase 3) |
| Live scraping / enrichment (CRE research source) | P3-4/P3-5 | Open (Needed by: Live research) |
| Production deployment approval | P3-7 | Open |
| Compliance jurisdiction | P3-4/P3-5 | **Resolved** — US MVP baseline (ADR_COMPLIANCE_JURISDICTION) |
| First-client manual-approval policy | P3-5 | **Resolved** — manual human approval per cold-email draft |
| Counsel-approved privacy/terms/outreach language | P3-5 | Open (Needed by: Live sending) |
| Production mock-provider exception | P3-7 | Open (default: no exception) |

## 6. Do-not-build / deferred (carried forward)

Real Stripe checkout/calls/webhooks/dunning/money movement · real SMS (A2P 10DLC/Twilio prod) ·
real mailbox provider delivery + bounce/complaint webhooks + warm-up · domain auth setup ·
Google/Meta ads connectors · Google Business Profile · live scraping/paid research (unless
approved) · automatic live sends from signal events · auto-send for first real client · privacy
export/delete/vector purge workflows (until built) · production deployment & live infra ·
Slack/internal alerts · full multi-plan self-serve pricing UI. (Sources: CLAUDE.md §3;
`evidence/phase-2-exit-completion.md` §9.)

## 7. Invariants that must NOT weaken in any Phase 3 slice

Tenant isolation + **forced RLS** · Clerk auth boundary + app-owned RBAC/object-auth/tenant
context/audit · billing gates (`is_active`, `has_feature`; derived CAN_SEND / CAN_RUN_AGENTS /
CAN_CREATE_CAMPAIGN / CAN_EXPORT) · idempotency (no duplicate sends/billing/imports/webhooks) ·
send gate (no send without a pass; dry-run never sends) · groundedness + re-grounding · human
approval · audit logs · rate limits · suppression/unsubscribe honors · no secrets in
logs/prompts/audit/exports/client responses. Do **not** remove `LocalMockNotice` /
`GateReasonBadge` until a production UX is explicitly designed and approved. (Sources:
ARCHITECTURE §5 mock-vs-real map; boot guard; CLAUDE.md non-negotiable rules.)

## 8. Phase 3 completion gate

Per `TESTING_AND_AUDIT.md`: each slice ships with tests + evidence; Phase 3 closes only with a
signed evidence bundle, all boot-guard conditions passing for the production target, backup
restore drill passed, and owner sign-off. Production go/no-go follows
`LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` §9.
