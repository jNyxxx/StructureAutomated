# P3-5i — Resend Secret-Resolution and Smoke Readiness Contract

**Purpose:** Define the secret-resolution boundary and readiness contract for a future internal-only Resend smoke.
**Status:** Docs-only contract complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `0f782fd docs(p3-5): prepare internal Resend smoke`

---

## 1. Scope and hard stop

P3-5i is documentation only. No code helper is required in this slice because the current code already has:

- Resend provider config validation for API secret ref, webhook secret ref when enabled, sending domain, and conservative cap values;
- production/staging boot-guard checks for unsafe Resend live-send/webhook config;
- disabled/fail-closed Resend adapter skeleton;
- fail-closed webhook route until real secret resolution is implemented.

Confirmed not done:

- no outbound email delivery;
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

## 2. Secret-ref requirements

Required before a future real internal smoke:

1. Resend API key secret ref.
2. Resend webhook signing secret ref when webhooks are included.
3. Refs must be non-placeholder.
4. Secret values must be resolved only through the approved secret backend.
5. Raw secret values must never be logged, returned, stored in DB rows, included in audit events, exposed to frontend, placed in screenshots, pasted into prompts, or committed to Git.
6. Future AWS Secrets Manager/KMS paths must follow the staging template convention.

Recommended staging secret-ref paths:

```text
/automatedstructure/staging/email/RESEND_API_KEY
/automatedstructure/staging/email/RESEND_WEBHOOK_SECRET
/automatedstructure/staging/kms/KEY_ALIAS
```

Required runtime behavior for future implementation:

- app config receives only secret refs, not secret values;
- secret resolver loads raw values in memory only at the adapter/verifier boundary;
- adapter/verifier errors must return only safe missing/invalid labels;
- secret refs may be logged only as redacted/present booleans, never full values;
- webhook secret resolution must remain separate from app-generic webhook secret config.

---

## 3. DNS / domain readiness

Required before a future real internal smoke:

- approved sending domain/subdomain is confirmed;
- DNS owner confirms SPF record status;
- DNS owner confirms DKIM record status;
- DNS owner confirms DMARC baseline status;
- return-path / bounce path is documented if required by provider setup;
- provider dashboard or CLI proof shows the domain is verified;
- proof reference is attached to the smoke evidence bundle.

No real provider delivery may run until DNS/domain verification proof exists.

---

## 4. Smoke owner values

Required owner/operator values:

- monitored Reply-To inbox;
- legal/company mailing details for the footer;
- exact internal smoke recipient;
- emergency-stop owner;
- deliverability-monitor owner;
- owner approval for a time-boxed smoke window.

These values must be recorded in private ops evidence when they contain personal data. Public docs should use redacted labels only.

---

## 5. Gate readiness

A future smoke may continue only if every runtime gate below passes:

- human review approval;
- send gate;
- suppression check;
- compliance profile;
- billing CAN_SEND / central billing gate;
- tenant rate limit;
- idempotency key;
- audit logging;
- webhook signature verification if webhook smoke is included;
- no automatic follow-up;
- no open/click tracking;
- internal recipient only.

A successful config readiness check is not enough to permit provider delivery. Runtime gates must still pass immediately before the provider boundary.

---

## 6. Readiness state definitions

| State | Meaning | Does it allow provider delivery? |
|---|---|---:|
| `config_ready` | Resend refs, sending domain, webhook ref if enabled, and caps are present and non-placeholder. | No |
| `smoke_ready` | `config_ready` plus DNS proof, owner values, monitored Reply-To, internal recipient, legal footer, rollback owner, and smoke-window approval. | No |
| `send_ready` | `smoke_ready` plus all runtime gates pass immediately before the provider boundary. | Internal-only smoke only |
| `production_ready` | Separate production release approval with launch blockers cleared, legal/provider approvals, staging proof, backups/alerts/rollback, and production cutover signoff. | Not granted by P3-5i |

P3-5i grants no readiness state by itself. It defines the contract only.

---

## 7. Secret-resolution boundary contract

Future implementation must follow this boundary:

1. Config stores secret refs only.
2. Boot guard validates refs are present and non-placeholder.
3. Smoke-readiness evidence confirms refs exist without showing values.
4. Secret resolver loads values only in the server runtime.
5. Adapter/verifier receives raw values only through dependency injection or a narrow resolver interface.
6. Raw values are never serialized, logged, audited, returned, stored, or exposed to the frontend.
7. Resolver failures fail closed.
8. Provider delivery remains disabled unless live-send flag, provider selection, and all gates are intentionally green for the smoke window.

Allowed future resolver output shape:

```text
api_key: loaded in memory only
webhook_secret: loaded in memory only
source: approved secret backend
redacted_ref: present
```

Disallowed future resolver output shape:

```text
api_key in logs
webhook_secret in errors
secret values in DB rows
secret values in frontend config
secret values in audit payloads
secret values in exported evidence
```

---

## 8. Hard stop conditions

A future smoke must stop if any of these are true:

- any required secret ref is missing;
- any required ref is placeholder-like;
- DNS/domain proof is missing;
- monitored Reply-To is missing;
- legal/company footer details are missing;
- internal recipient is missing;
- emergency-stop owner is missing;
- deliverability owner is missing;
- rollback plan is missing;
- human approval is missing;
- any runtime gate fails;
- idempotency key is missing or reused incorrectly;
- any real customer/prospect recipient is present;
- open/click tracking is enabled without approval;
- raw secret, raw webhook body, recipient PII, or raw provider payload appears in logs/responses/evidence;
- webhook verification is not configured when webhook smoke is included;
- provider delivery code is not the explicitly approved smoke implementation;
- production release approval is confused with internal-smoke approval.

---

## 9. Required later smoke evidence

A future internal-smoke evidence bundle must include:

- source commit SHA;
- environment name;
- readiness state claimed and why;
- config summary with redacted refs;
- DNS verification proof reference;
- secret refs present, values redacted;
- Reply-To owner confirmation;
- legal footer confirmation;
- internal recipient confirmation, redacted in public evidence;
- emergency-stop owner and deliverability owner confirmations;
- smoke-window approval reference;
- idempotency key reference;
- human-review approval ID;
- send-gate result ID;
- suppression/compliance/billing/rate-limit gate results;
- provider message ID if delivery occurs in the later approved slice;
- webhook event result if webhook smoke is included;
- audit event ID;
- log review result proving no secret/PII leakage;
- rollback/emergency-stop result.

---

## 10. Current missing values / blockers

Still missing after P3-5i:

- real Resend adapter implementation approval;
- secret resolver implementation approval;
- Resend API secret ref;
- Resend webhook signing secret ref/resolution;
- DNS verification proof;
- monitored Reply-To confirmation;
- legal/company footer details;
- internal smoke recipient;
- emergency-stop owner;
- deliverability-monitor owner;
- smoke-window approval;
- durable webhook-event persistence decision;
- outbound status mutation decision;
- external-recipient approval remains out of scope.

---

## 11. Final verdict

P3-5i is complete as a secret-resolution and smoke-readiness contract.

It does not make the system config-ready, smoke-ready, send-ready, or production-ready by itself. It only defines the conditions a later approved implementation/smoke slice must satisfy.
