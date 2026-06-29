> **SCOPE CORRECTION — P3-5j (2026-06-29):** This document recorded P3-5e
> decisions before the dual-layer architecture was established. Key corrections:
> - `outreach.automatedstructure.com` is now designated for **transactional/opted-in**
>   sends via Resend, not cold outreach.
> - Cold outreach uses a separate mailbox-pool manager (future, mocked for MVP).
> - The unsubscribe footer language below ("...we found your business contact for
>   relevant B2B outreach") was drafted for cold outreach and must NOT be used for
>   transactional Resend sends. Transactional footer is TBD pending legal review.
> - All other values (caps, webhook scope, emergency stop) remain valid.
> See `docs/evidence/phase-3-5j-dual-sending-layer-scope-correction.md`.

---

# P3-5e — Owner Approval + Resend Roadmap

**Purpose:** Record the owner's answers to the P3-5d real-sending decision packet, the selected provider (Resend), the safe defaults that remain in force, the concrete values still required before any live smoke, and the post-approval Phase 3 sending roadmap.
**Status:** Owner approval recorded — provider lane selected, **real sending still disabled**. Adapter implementation NOT started.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `369df75 test(p3-4): add endpoint rate limit coverage`
**Class:** docs-only (planning / approval capture).
**Answers to:** [phase-3-5d-real-sending-owner-decision-packet.md](phase-3-5d-real-sending-owner-decision-packet.md)

---

## 1. What this slice is — and is NOT

This slice **records owner decisions only**. It does not implement anything.

Explicitly **not done** in P3-5e (carried forward, still gated):

- No Resend adapter (owner: *"Do not implement the Resend adapter yet."*).
- No provider SDK added. No credentials added. No `.env` edits.
- No Resend API call. No webhook endpoint. No DNS implementation.
- No live email sending. No production. No deploy.
- No Stripe, no SMS, no live scraping.
- No bypass of human approval, send gate, suppression, compliance, billing, idempotency, or rate limits.

Safe defaults remain exactly as P3-5b shipped them:

- `EMAIL_PROVIDER=mock`
- `LIVE_EMAIL_SENDING_ENABLED=false`
- Only the network-free `MockEmailSendProvider` is registered; the production boot guard fails closed on any non-mock provider, live-send enablement without required secret/domain config, or `controlled_demo` live-send bypass.

---

## 2. Owner approval — recorded

The owner answered the P3-5d packet on **2026-06-28**. The thirteen decisions are recorded below verbatim in intent. Real-sending implementation (P3-5f+) may begin **only** after the remaining concrete values in §4 are supplied and recorded.

| # | Decision | Owner answer |
|---|---|---|
| 1 | **Email provider** | **Resend** is selected as the main email provider. |
| 2 | **Sending domain / subdomain** | Default sending subdomain `outreach.automatedstructure.com` unless owner later changes it. |
| 3 | **DNS owner** | Owner/business controls DNS. Engineering may prepare required records; DNS owner must add and verify Resend SPF/DKIM/DMARC/return-path records. |
| 4 | **Sender identity** | Default `From: AutomatedStructure <outreach@outreach.automatedstructure.com>`. Default `Reply-To: replies@automatedstructure.com` (or another monitored owner-provided inbox). |
| 5 | **Legal / unsubscribe copy** | Required unsubscribe footer on **all** outbound email. Default copy: *"You are receiving this because we found your business contact for relevant B2B outreach. To stop receiving emails, unsubscribe here: {{unsubscribe_url}}."* Company/legal mailing details to be added once final business address confirmed. |
| 6 | **Send caps (first pilot, conservative)** | tenant hourly = **10**; tenant daily = **50**; campaign daily = **50**; mailbox/sender daily = **25**. |
| 7 | **Sandbox / internal smoke** | Approved **only after** DNS verification, Resend secret_ref setup, webhook secret_ref setup, legal footer, and all send gates pass. First real smoke is **internal-only**. No prospect/client sending during first smoke. |
| 8 | **Webhook events** | Accept normalized events: `delivered`, `bounced`, `complained`, `deferred`, `failed`, and `unsubscribed/suppressed` if supported by the normalized Resend event shape. Open/click tracking **not** enabled unless explicitly enabled later. |
| 9 | **Webhook safety** | Signature verification **required**. Idempotency **required**. No raw webhook payload leakage. |
| 10 | **Deliverability owner** | Owner/operator monitors bounces, complaints, DNS health, provider blocks, suppressions, warm-up — until a dedicated ops owner exists. |
| 11 | **Emergency stop owner** | Owner/operator **and** engineering can emergency-stop sending. Emergency stop must disable live sending immediately via config/feature flag. |
| 12 | **Provider account owner** | Owner/operator owns the Resend account. Engineering configures secret refs / integration only through approved secret/config paths. |
| 13 | **Concrete pre-smoke values** | Still outstanding — see §4. |

---

## 3. Resend decision rationale (recorded)

P3-5c compared Amazon SES, SendGrid, Postmark, Mailgun, and Resend and recommended SES (if AWS remains target) or Postmark (fastest operator workflow) as non-final defaults. The owner has now **selected Resend** as the main provider. This is the binding decision; the P3-5c recommendation is superseded for provider choice.

Implications for the adapter slice (P3-5f, future):

- Resend HTTP API + official webhook signing (`svix`-style signature header) must be wired behind the existing `EmailSendProvider` Protocol and fail-closed `EmailProviderRegistry`.
- Webhook event names must be normalized to the §2.8 set; no open/click tracking.
- Provider API key and webhook signing secret are **secret refs only**, loaded from AWS Secrets Manager/KMS in production (never DB rows, logs, audit, prompts, exports, frontend, or client responses).

---

## 4. Remaining concrete values required before live smoke

Real-sending work past the adapter design boundary is **blocked** until these are supplied and recorded:

1. Actual Resend **API secret ref**.
2. Actual Resend **webhook signing secret ref**.
3. Confirmed **DNS verification** (SPF/DKIM/DMARC/return-path green on `outreach.automatedstructure.com`).
4. Final monitored **Reply-To inbox**.
5. Final **legal/company mailing details** (if required for footer).
6. Exact **internal smoke recipient** address.
7. Final **emergency-stop owner** name.
8. Final **deliverability-monitor owner** name.

---

## 5. Post-approval Phase 3 sending roadmap

| Slice | Goal | Class | Stop gate |
|---|---|---|---|
| **P3-5e** *(this slice)* | Record owner approval + Resend decision + safe defaults + roadmap | docs-only | Done — committed. |
| **P3-5f** | Resend adapter skeleton + provider config validation (behind flag, fail-closed; secret-ref only) | real provider integration | Requires §4 secret refs recorded; defaults stay mock/live-disabled; no live call in this slice (sandbox/test wiring only). |
| **P3-5g** | Secret-ref wiring (AWS Secrets Manager/KMS) + DNS verification implementation + signed, idempotent webhook endpoint + normalized event persistence | real provider integration | Requires §4.1–§4.3 green; webhook signature verify + dedupe enforced; no PII/secret leakage. |
| **P3-5h** | Provider sandbox/test smoke → **internal-only** real email smoke | real provider integration | Requires all of §4; all send gates pass; internal recipient only; no prospect/client sends; smoke result approved by owner. |
| **P3-5i** *(separate approval)* | External-recipient sending | real provider integration — **DEFERRED** | Requires counsel-approved legal copy + green internal-smoke evidence + separate written owner approval. |

Invariants preserved across every future slice: mock-disabled/live-disabled defaults, fail-closed boot guard, send gate before provider call, manual human approval, suppression/compliance/billing/rate-limit checks, idempotency + duplicate-send prevention, no raw secrets or raw provider payloads in logs/audit/frontend/client responses.

---

## 6. Docs changed in this slice

- `docs/evidence/phase-3-5e-owner-approval-resend-roadmap.md` (new — this file).
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` — §1 verdict, §2 resolved decision row, §6 sending blocker row, §7 remaining decisions.
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md` — new §4C owner-approved sending decisions (provider, subdomain, sender identity, footer copy, first-pilot caps, webhook scope, internal-smoke-only, emergency stop).
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md` — §4 slice plan P3-5 row + execution order; §5 owner decisions status.
- `docs/DOCUMENTATION_MANIFEST.md` — new P3-5e evidence row.
- `docs/OPERATIONS_RUNBOOK.md` — §B1 email-provider config: Resend pilot decision + conservative caps + emergency-stop flag note.

---

## 7. Verification

- Docs-only slice. No backend/frontend code, DB migrations, tests, package/config/Docker/app files, or master guide changed.
- No SDK, credential, `.env`, provider call, live sending, production, deploy, Stripe, SMS, or live-scraping change.
- Test gates unchanged from P3-4 close (backend 598 / frontend 122). Not re-run — no code touched.

---

## 8. Final verdict

Owner approval **recorded**. Resend selected as the pilot email provider. Real sending **remains disabled**; the Resend adapter is **not** implemented. P3-5f and beyond are unblocked for design/skeleton work but cannot reach a live or even internal-smoke send until the eight concrete values in §4 are supplied and recorded, and all send gates pass. No production, provider, or money-movement surface is reachable from this slice.
