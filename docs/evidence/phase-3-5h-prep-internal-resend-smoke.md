# P3-5h-prep — Internal-Only Resend Smoke Preparation

**Purpose:** Prepare the exact checklist, config/secret contract, evidence requirements, and rollback plan for a later internal-only Resend smoke.
**Status:** Docs-only preparation complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `4d68eb8 feat(p3-5): add Resend webhook verification foundation`

---

## 1. Scope and hard stop

P3-5h-prep is documentation only. No code boundary is required because P3-5f and P3-5g already provide the disabled adapter skeleton, webhook verification foundation, route skeleton, idempotency boundary, and boot-guard checks.

Confirmed not done:

- no real email sent;
- no live-send flag enabled;
- no Resend API call;
- no Resend SDK added;
- no real credentials added;
- no real environment file edited;
- no deployment;
- no image registry upload;
- no AWS provisioning;
- no production enablement;
- no Stripe, SMS, or live scraping;
- no human-review bypass;
- no send-gate, suppression, compliance, billing, rate-limit, or idempotency bypass;
- no auth/RBAC/RLS/tenant-isolation change;
- no boot-guard weakening.

---

## 2. Current state before real smoke

Current implementation state:

- Resend is selected by owner as the provider direction.
- Resend adapter exists only as a disabled, fail-closed skeleton.
- Send attempts through the skeleton fail safely.
- Resend webhook route exists only as a verification/normalization foundation.
- Default webhook route dependency remains fail-closed because real secret resolution is deferred.
- Open/click tracking remains disabled/ignored.
- Durable webhook-event persistence is still deferred.
- Outbound status mutation from webhook events is still deferred.

Therefore, a future real internal smoke still requires a separate approved implementation slice before any provider call is reachable.

---

## 3. Required concrete values before real smoke

All values below must be supplied, reviewed, and recorded before a later P3-5h real-smoke slice starts:

1. Resend API secret reference.
2. Resend webhook signing secret reference.
3. Confirmed DNS verification for the approved sending domain/subdomain.
4. Monitored Reply-To inbox.
5. Legal/company mailing details for the required footer.
6. Exact internal smoke recipient.
7. Emergency-stop owner name.
8. Deliverability-monitor owner name.

No raw values may be pasted into Git, docs, prompts, logs, audit events, frontend config, client responses, or screenshots.

Recommended redacted evidence format:

```text
Resend API secret ref: present, redacted
Webhook signing secret ref: present, redacted
DNS verification: passed, proof reference attached
Reply-To inbox: monitored, owner confirmed
Legal footer details: present, redacted where needed
Internal smoke recipient: internal-only, redacted in public evidence
Emergency-stop owner: named in private ops tracker
Deliverability owner: named in private ops tracker
```

---

## 4. Required gates before a real smoke

A later real-smoke slice must not proceed unless every gate below is green:

| Gate | Required state |
|---|---|
| Provider adapter | Real Resend adapter implemented in a separately approved slice. |
| Provider SDK/API boundary | Explicitly reviewed; no raw secret/payload leakage. |
| Webhook verification | Configured with approved webhook signing secret path. |
| DNS | Verified for sending subdomain/domain. |
| Provider selection | Resend selected intentionally for smoke. |
| Live-send flag | Enabled only for the smoke window, with approval. |
| Provider webhooks | Enabled only if webhook smoke is included. |
| Caps | Tenant hourly/day, campaign/day, and mailbox/day caps set conservatively. |
| Human review | Approved draft exists. |
| Send gate | Passes before provider call. |
| Suppression | Recipient is not suppressed. |
| Compliance profile | Footer, company details, and policy checks pass. |
| Billing | CAN_SEND / central billing gate passes. |
| Tenant rate limit | Passes. |
| Idempotency | Idempotency key is present and unique for smoke. |
| Audit logging | Enabled and verified. |
| Secrets | Secret refs present; raw values never exposed. |
| Logs | Structured logs checked for secret/PII leakage. |

If any gate fails, stop the smoke.

---

## 5. Internal smoke scenario

The later real-smoke scenario must be exactly limited to:

1. One email only.
2. Internal recipient only.
3. No prospect, client, customer, scraped, imported, or third-party recipient.
4. Subject clearly marked as internal smoke.
5. Body clearly marked as internal smoke.
6. Body includes the approved unsubscribe footer placeholder or real unsubscribe link if available.
7. Human-approved draft only.
8. Send gate dry-run passes before send intent.
9. Send intent uses one unique idempotency key.
10. Provider result records safe `provider_message_id` only.
11. No automatic follow-up.
12. No open/click tracking.
13. Webhook events reconciled if available.
14. Logs reviewed immediately after the smoke.
15. Emergency stop tested after smoke if safe to do so.

Allowed internal-smoke email content shape:

```text
Subject: [INTERNAL SMOKE] AutomatedStructure Resend delivery test
Body: This is an internal-only smoke test for AutomatedStructure email delivery. No prospect or client recipient is included.
Footer: You are receiving this because this address was approved for internal testing. Unsubscribe: <approved-placeholder-or-link>
```

Do not send to any real prospect/client recipient during the first smoke.

---

## 6. Rollback / emergency stop plan

Immediate stop actions:

1. Turn the live-send flag off.
2. Optionally set provider selection back to mock.
3. Revoke or rotate the Resend API key if misuse or leakage is suspected.
4. Disable provider webhook config if webhook abuse or signature failure is suspected.
5. Record incident owner and timestamp.
6. Confirm send-intents fail closed after the stop.
7. Confirm no follow-up automation was scheduled.
8. Review logs/audit for unexpected recipient, duplicate send, or secret leakage.

Post-stop checks:

- `/api/v1/send-gate/dry-run` can still evaluate safely.
- `/api/v1/send-intents` cannot reach live provider delivery.
- Resend webhook route still verifies signatures before normalization.
- Audit trail includes the stop action.
- Owner/operator acknowledges the stop result.

---

## 7. Evidence required for the later real smoke

A future P3-5h real-smoke evidence bundle must include:

- source commit SHA;
- environment name;
- config summary with values redacted;
- DNS verification screenshot, CLI proof, or provider proof reference;
- secret refs present, values redacted;
- monitored Reply-To owner confirmation;
- legal/company footer confirmation;
- internal smoke recipient, redacted in public evidence;
- emergency-stop owner and deliverability owner, recorded in private ops tracker;
- idempotency key, redacted if policy requires;
- human review approval ID;
- send-gate result ID;
- suppression/compliance/billing/rate-limit gate results;
- provider message ID;
- webhook event result if available;
- audit event ID;
- log review result showing no secret leakage;
- emergency stop / rollback result;
- owner signoff.

Do not include raw email body if it includes PII. Include a sanitized sample or template only.

---

## 8. Hard stop conditions

A later real-smoke slice must stop immediately if any of these are true:

- DNS is not verified.
- Resend API secret ref is missing.
- Resend webhook signing secret ref is missing when webhook smoke is included.
- Monitored Reply-To inbox is missing.
- Legal footer/company details are missing.
- Internal recipient is missing.
- Emergency-stop owner is missing.
- Deliverability owner is missing.
- Human review approval is missing.
- Send gate fails.
- Suppression check fails.
- Compliance gate fails.
- Billing CAN_SEND fails.
- Tenant rate limit fails.
- Idempotency key is missing or reused incorrectly.
- Raw secret leakage is detected.
- Any real customer/prospect recipient is present.
- Open/click tracking is enabled without approval.
- Logs expose raw webhook body, secret, signature, recipient PII, or provider raw payload.
- Rollback/emergency-stop path is not ready.

---

## 9. Current blockers for real smoke

The later real-smoke slice remains blocked on these missing values/work items:

- real Resend adapter implementation;
- secret resolution from approved secret path;
- Resend API secret ref;
- webhook signing secret ref;
- DNS verification;
- monitored Reply-To;
- legal/company mailing details;
- internal smoke recipient;
- emergency-stop owner name;
- deliverability-monitor owner name;
- durable webhook-event persistence if required for smoke evidence;
- owner approval for a time-boxed live-send smoke window.

---

## 10. Final verdict

P3-5h-prep is complete.

The future internal-only Resend smoke is fully specified, but remains blocked until the concrete values and a separately approved real-adapter/smoke slice are supplied.
