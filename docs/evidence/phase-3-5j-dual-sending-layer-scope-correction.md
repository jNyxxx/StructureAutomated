# Phase 3-5j: Dual Sending-Layer Scope Correction

**Date:** 2026-06-29
**Status:** Complete
**Slice type:** Architecture correction + code guard + docs update
**Prerequisite:** P3-5i (Resend secret readiness contract)

---

## 1. Owner Decision Summary

Owner decision recorded 2026-06-29:

| Decision | Value |
|---|---|
| Resend scope | Transactional / opted-in ONLY (autoresponders, drip to opted-in, system notifications) |
| Cold outreach scope | Separate dedicated mailbox-pool manager — future phase, mocked for MVP |
| Resend account owner | William |
| DNS owner | William |
| Deliverability monitor owner | William |
| Emergency-stop owner | William |
| Resend API secret ref target | `RESEND_API_KEY` |
| Resend webhook secret ref target | `RESEND_WEBHOOK_SECRET` |
| Resend mock flag | `RESEND_USE_MOCK` |
| Transactional sending subdomain | `outreach.automatedstructure.com` |
| Transactional From identity | `outreach@outreach.automatedstructure.com` |
| Transactional Reply-To | `replies@automatedstructure.com` (configurable, not hardcoded) |
| Legal footer | Placeholder: `[LEGAL ENTITY NAME]` / `[PHYSICAL MAILING ADDRESS]` |
| First internal smoke recipient | William only |
| Open/click tracking | Disabled by default |
| Nothing live until | First paying client or explicit owner approval |

---

## 2. Architecture Correction

Prior P3-5 docs (P3-5a through P3-5i) positioned Resend as the cold-outreach
provider on `outreach.automatedstructure.com`. Owner decision on 2026-06-29
reverses this:

### Corrected Dual Sending-Layer Architecture

| Layer | Provider | Status | Purpose |
|---|---|---|---|
| **Transactional / opted-in** | Resend | Skeleton (live disabled) | Autoresponders, drip to opted-in, system notifications |
| **Cold outreach** | Mailbox-pool manager | Future, mocked for MVP | B2B cold sends via per-inbox warm-up, rotation, dedicated cold subdomains |

### Transactional Layer (Resend)
- Subdomain: `outreach.automatedstructure.com` (transactional use)
- From: `outreach@outreach.automatedstructure.com`
- Reply-To: `replies@automatedstructure.com` (configurable)
- Caps: tenant 10/hr / 50/day; campaign 50/day; mailbox 25/day
- Open/click tracking: disabled by default
- Live sending: DISABLED until DNS verified, secrets resolved, legal copy approved, internal smoke passed

### Cold Outreach Layer (mailbox-pool, future)
- Provider: dedicated mailbox-pool manager (future phase, not P3-5)
- Sending subdomains: not yet acquired or configured
- Per-inbox caps: 30–50 sends/inbox/day
- Rotation: across multiple inboxes
- Warm-up: 10-day ramp; clock mocked for MVP
- Actual send: mocked for MVP
- Must NOT route through Resend, SendGrid, or any transactional/bulk ESP

---

## 3. Code Guard Summary

### What changed

**`backend/app/services/email_provider.py`:**
- Added `ColdOutreachNotAllowedOnTransactionalProvider(AppError)` — code `COLD_OUTREACH_NOT_ALLOWED`, status 422
- Added `send_layer: Literal["transactional", "cold_outreach"] = "cold_outreach"` to `ProviderSendRequest`
- `ResendEmailSendProvider.send()` now raises `ColdOutreachNotAllowedOnTransactionalProvider` before `LiveEmailProviderDisabled` when `send_layer == "cold_outreach"`

### Why default = "cold_outreach"

All existing send-intents (B2B campaign sends) are cold outreach. Default fail-closed:
any call that does not explicitly pass `send_layer="transactional"` is rejected by
Resend. Future transactional callers must opt-in explicitly.

### Why no change to MockSenderService

`MockSenderService.send_approved_draft()` constructs `ProviderSendRequest` without
`send_layer`. The default `"cold_outreach"` is correct — existing sends are cold
outreach and they route to `MockEmailSendProvider`, which accepts both layers.
No change is needed until a transactional send path is built.

---

## 4. Config Alignment

| Variable | Value | Meaning |
|---|---|---|
| `EMAIL_PROVIDER` | `mock` (default) | Mock adapter; no live provider |
| `LIVE_EMAIL_SENDING_ENABLED` | `false` (default) | Live Resend sends disabled |
| `RESEND_USE_MOCK` | `true` (future placeholder) | When Resend is implemented: use mock Resend client instead of real API |
| `EMAIL_SENDING_DOMAIN` | placeholder | Must be `outreach.automatedstructure.com` (transactional) when live |
| `EMAIL_REPLY_TO` | not in config yet | Will be `replies@automatedstructure.com`; must be configurable, not hardcoded |

Reply-To and legal footer (legal entity name, physical mailing address) are
configurable placeholders. Not hardcoded into business logic.

---

## 5. Emergency-Stop Requirement

### Transactional layer (Resend)
`LIVE_EMAIL_SENDING_ENABLED=false` — existing mechanism. Owner/operator and engineering
can set this flag immediately to stop all transactional Resend sends.

### Cold outreach layer (future)
No kill switch exists yet. **Hard blocker for the mailbox-pool manager phase:**
`LIVE_COLD_SENDING_ENABLED=false` (or equivalent flag) must exist before that
layer goes live. Kill switch must be fast and not buried in config.

One owner-triggerable kill switch must disable each layer independently. Both
must be documented in the ops runbook with owner contact and response time.

---

## 6. Tests Added / Updated

| Test | Change |
|---|---|
| `test_resend_rejects_cold_outreach_send_layer` | New — cold_outreach → 422 COLD_OUTREACH_NOT_ALLOWED |
| `test_resend_rejects_cold_outreach_even_when_live_enabled` | New — cold_outreach rejected before live check |
| `test_resend_cold_outreach_rejection_exposes_no_secrets_or_domain` | New — no secrets/domain leaked in error |
| `test_resend_skeleton_is_disabled_for_send_attempts_without_live_flag` | Updated — uses `_transactional_request()` |
| `test_complete_resend_skeleton_still_cannot_send_or_expose_secret_refs` | Updated — uses `_transactional_request()` |
| `test_provider_send_request_defaults_send_layer_to_cold_outreach` | New — default field value check |
| `test_mock_provider_accepts_both_send_layers` | New — mock is unrestricted |

---

## 7. Honest Limits

- No real Resend API call made.
- No Resend SDK imported.
- No real credentials added.
- No live email sent.
- No cold outreach live send enabled.
- No DNS configured.
- No cold-sending domains acquired or configured.
- No Stripe money movement.
- No production environment enabled.
- No deployment performed.
- `RESEND_USE_MOCK` is a documented placeholder; implementation deferred to live adapter phase.
- Cold outreach mailbox-pool manager is a future phase — not designed, not planned, not implemented here.
