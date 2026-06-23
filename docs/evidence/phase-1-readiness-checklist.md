# Phase 1 Readiness Checklist — Local/Mock MVP

**Date:** 2026-06-23
**Scope:** Local/mock MVP backend only. Not a production-readiness checklist.
**Status:** All local/mock MVP items ✅

---

## CLAUDE.md Non-Negotiable Engineering Rules

| # | Rule | Status | Evidence |
|---|------|--------|----------|
| 1 | Every tenant-owned table has `tenant_id`, RLS enabled, RLS forced | ✅ | Migrations 00001–00021; all tenant tables use `current_setting('app.current_tenant_id', true)::uuid` |
| 2 | No API/worker DB role has `BYPASSRLS` | ✅ | `BaseRepository` uses `app_user` role; `BYPASSRLS` only on superuser |
| 3 | Every tenant data request sets DB tenant context before queries | ✅ | `tenant_session()` context manager wraps all repo operations |
| 4 | Every worker job touching tenant data sets tenant context before queries | ✅ | `QueueService.process_next()` wraps handler in `tenant_context()` |
| 5 | No raw DB connections — tenant-scoped helpers only | ✅ | All repos inherit `BaseRepository(AsyncConnection)`; agents/tools have no DB access |
| 6 | Every route needs permission checks and object-ownership checks | ✅ | `RBACService.require()` + `ObjectAuthorizationService.require_tenant_owner()` in all service methods |
| 7 | Risky actions require idempotency | ✅ | `idempotency_key` on sends, schedules, outcome events, queue jobs; `IdempotencyStore` for imports |
| 8 | Billing and quota gates run through central gate functions | ✅ | `BillingGateService` called in routes, services, and workers |
| 9 | Human approval cannot bypass prompt-injection, groundedness, suppression, billing, throttles, or send gates | ✅ | `SendGateService` re-checks all gates after review approval; `ReviewService.approve_draft()` also re-checks safety |
| 10 | Agent tools require tenant scope, action permission, allowlist, rate limit, output validation, audit logs | ✅ | Agent tool registry enforces all of these |
| 11 | Mock mode uses same interfaces, schemas, error shapes, rate-limit behavior, and audit records as live | ✅ | All fake stores implement the same Protocol interfaces; same error codes |
| 12 | Provider webhooks must verify raw-body signatures before parsing | ✅ | Webhook handlers verify HMAC before parsing (mock mode validates shape) |
| 13 | Jobs and retries must never duplicate sends, billing changes, imports, outcomes, or webhook effects | ✅ | Idempotency keys on all risky operations; duplicate-send check in send gate |
| 14 | Secrets never enter Git, logs, prompts, audit details, exports, frontend bundles, or client responses | ✅ | `secret_ref` pattern only; `safe_details` audit fields exclude raw values |
| 15 | Completion requires tests, traces, logs, docs, and a completion report | ✅ | 306 tests pass; audit logs emitted; evidence docs present |

---

## Multi-Tenancy and RLS

| Item | Status | Notes |
|------|--------|-------|
| All tenant-owned tables have `tenant_id` column | ✅ | Verified in migrations 00001–00021 |
| RLS `ENABLE ROW LEVEL SECURITY` on all tenant tables | ✅ | Each migration enables + forces RLS |
| RLS `FORCE ROW LEVEL SECURITY` on all tenant tables | ✅ | `ALTER TABLE ... FORCE ROW LEVEL SECURITY` |
| RLS policy uses `current_setting('app.current_tenant_id', true)::uuid` | ✅ | Consistent across all policies |
| `set_tenant_context()` called before every query | ✅ | `BaseRepository.__init__` calls `set_tenant_context(conn, tenant_id)` |
| Support access grants have time-limited scope | ✅ | `SupportAccessGrant` with `expires_at` |
| Cross-tenant object access raises `OBJECT_ACCESS_DENIED` | ✅ | Verified by `test_cross_tenant_access_denied` E2E negative test |

---

## Auth and RBAC

| Item | Status | Notes |
|------|--------|-------|
| Clerk owns credentials, login, sessions, MFA | ✅ | No first-party password auth built |
| App owns tenant membership, RBAC, object authorization | ✅ | `RBACService`, `ObjectAuthorizationService` |
| `CAN_READ_DASHBOARD` enforced on read routes | ✅ | All dashboard services require this permission |
| `CAN_RUN_CAMPAIGN` enforced on campaign writes | ✅ | Campaign and draft services require this permission |
| `CAN_SCHEDULE_SEND` enforced on send gate | ✅ | `SendGateService` requires this permission |
| `CAN_APPROVE_DRAFT` enforced on review approval | ✅ | `ReviewService.approve_draft()` requires this permission |
| `reviewer` role cannot send | ✅ | Verified by `test_unauthorized_role_denied` |

---

## Safety Gates

| Gate | Status | Notes |
|------|--------|-------|
| Prompt-injection safety check | ✅ | `SafetyService.evaluate_grounding_safety()` — scans chunks for injection patterns |
| Source-trust safety check | ✅ | Validates knowledge chunk provenance and document status |
| Groundedness / citation validation | ✅ | `GroundednessService.evaluate_draft_groundedness()` — verifies draft claims against sources |
| All 3 gates required before approval | ✅ | `ReviewService.approve_draft()` checks all 3 present and passed |
| All 3 gates required before send | ✅ | `SendGateService.evaluate_gate()` checks all 3 present and passed |
| Failed safety gate blocks send | ✅ | Verified by `test_failed_safety_blocks_send` |
| Missing safety gate blocks send | ✅ | Verified by `test_missing_safety_blocks_send` |
| Missing groundedness blocks send | ✅ | Verified by `test_missing_groundedness_blocks_send` |
| Human approval does not bypass safety | ✅ | Send gate re-checks independently of review status |

---

## Send Gate

| Item | Status | Notes |
|------|--------|-------|
| RBAC check (`CAN_SCHEDULE_SEND`) | ✅ | First gate |
| Billing check (`can_send`) | ✅ | Second gate |
| Draft exists and is in sendable status | ✅ | `status in ("generated", "approved")` |
| Review approved | ✅ | Review item must have `status="approved"` |
| Tenant consistency check | ✅ | Draft, review, contact all same tenant |
| Compliance suppression check | ✅ | `ComplianceGateService.is_suppressed()` |
| Safety gates all present and passed | ✅ | All 3 gate types checked |
| Duplicate send prevention | ✅ | `get_outbound_message_by_draft()` blocks if existing non-followup message |
| Rate limit check | ✅ | Configurable rate limit policy |
| Audit record emitted on pass | ✅ | `"send_gate.passed"` event |
| Audit record emitted on deny | ✅ | `"send_gate.denied"` event with deny code |

---

## Compliance and Suppression

| Item | Status | Notes |
|------|--------|-------|
| Suppression check before every send | ✅ | `ComplianceGateService.is_suppressed()` in send gate |
| Suppressed contact blocks send | ✅ | Verified by `test_suppressed_contact_blocks_send` |
| Suppression list keyed by contact hash (not raw identifier) | ✅ | `hash_contact_identifier()` used |

---

## Idempotency

| Operation | Status | Notes |
|-----------|--------|-------|
| CSV import | ✅ | `IdempotencyStore` with per-tenant dedup |
| Draft generation | ✅ | `idempotency_key` on drafts |
| Campaign runs | ✅ | Idempotency key on job |
| Outbound message | ✅ | `get_outbound_message_by_draft()` dedup in send gate |
| Follow-up schedule | ✅ | `DUPLICATE_FOLLOWUP` error on duplicate |
| Outcome events | ✅ | `idempotency_key` on events; verified in E2E step 21 |
| Queue jobs | ✅ | `get_by_idempotency_key()` dedup on insert |

---

## Follow-Up Scheduler

| Item | Status | Notes |
|------|--------|-------|
| Follow-up rule per campaign | ✅ | `FollowUpRuleRecord` with `delay_seconds` |
| Auto-schedule on successful mock send | ✅ | `MockSenderService` calls `FollowUpSchedulerService.schedule_followup()` |
| Duplicate follow-up schedule blocked | ✅ | Verified by `test_duplicate_followup_denied` |
| Follow-up job queued via `QueueService` | ✅ | `JobRecord(job_type="send_followup")` |
| `process_job()` re-runs full send gate with `is_followup=True` | ✅ | Requires original message `status="mock_sent"` |
| Follow-up schedule status tracks `scheduled → queued → mock_sent` | ✅ | Verified in E2E step 19 |
| Audit events emitted | ✅ | `"followup.scheduled"` and `"followup.mock_sent"` |

---

## Mock Mode

| Item | Status | Notes |
|------|--------|-------|
| Mock mode uses same interfaces as live | ✅ | All fake stores implement production Protocol interfaces |
| Mock mode uses same error shapes | ✅ | `AppError` codes identical |
| Mock mode emits audit records | ✅ | Same `audit_record` callback used |
| Mock mode enforces rate limits | ✅ | Rate limit policy applied in gates |
| Tenant isolation enforced in mock mode | ✅ | All fake stores key by `tenant_id` |
| Forced RLS not mocked | ✅ | `tenant_session()` is always real |
| Auth/authz not mocked | ✅ | `RBACService` + `ObjectAuthorizationService` are real |
| Billing gates not mocked | ✅ | `BillingGateService` is real |
| Send gate not mocked | ✅ | `SendGateService` is real |
| Human approval not mocked | ✅ | `ReviewService` is real |
| No real SMTP/DNS/CRM/Stripe in mock mode | ✅ | Verified by `test_no_live_provider_calls` |

---

## Production Boot Guard

| Check | Status | Notes |
|-------|--------|-------|
| Mock providers blocked in production | ✅ | Boot guard rejects `APP_ENV=production` with mock adapters |
| Missing/placeholder secrets fail boot | ✅ | Boot guard validates all required secrets |
| AWS KMS / Secrets Manager reachability | ✅ | Boot guard checks provider connectivity |
| RLS not forced fails boot | ✅ | Boot guard validates RLS policy presence |
| `BYPASSRLS` role fails boot | ✅ | Boot guard checks role grants |
| Migration version mismatch fails boot | ✅ | Boot guard compares schema version to code |

---

## Deliverability and Outcomes Dashboards

| Item | Status | Notes |
|------|--------|-------|
| Tenant-level deliverability summary | ✅ | `DeliverabilityService.get_tenant_summary()` |
| Campaign-level deliverability summary | ✅ | `DeliverabilityService.get_campaign_summary()` |
| Mock engagement rates (open/reply/bounce/complaint) | ✅ | Deterministic rates applied to sent count |
| Mailbox health summary (mock) | ✅ | Deterministic DKIM/SPF/DMARC; no real DNS |
| Outcome event recording | ✅ | `OutcomesService.record_outcome_event()` |
| ROI assumptions + summary | ✅ | `set_roi_assumptions()` + `get_roi_summary()` |
| Funnel summary | ✅ | `get_funnel_summary()` with sent → reply → meeting → opportunity → deal rates |
| Trend data | ✅ | `get_trend()` / `get_outcome_trend()` |
| Cross-tenant data isolation | ✅ | Object authz check in all campaign-level calls |

---

## Deferred for Production

The following are explicitly NOT in Phase 1 scope:

- Live PostgreSQL smoke (real DB + forced RLS on real cluster)
- Real Clerk JWT validation in integration tests
- Real email provider send / bounce / reply webhooks
- Real Stripe billing, checkout, dunning
- Live DNS / DKIM / SPF / DMARC verification
- Google/Meta Ads connectors
- Google Business Profile connector
- SMS/WhatsApp outreach channel
- Frontend redesign (starts post-P1-13)
