# P3-5g — Resend Webhook Verification and Event Normalization Foundation

**Purpose:** Add Resend webhook signature verification, safe event normalization, and idempotency boundary without enabling real sending.
**Status:** Complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `b2b3253 feat(p3-5): add Resend adapter skeleton`

---

## 1. Scope and hard stop

P3-5g adds webhook verification and normalization foundation only.

Confirmed not done:

- no real email delivery;
- no Resend API call;
- no Resend SDK;
- no real credentials;
- no real environment file edit;
- no deployment;
- no image registry upload;
- no AWS provisioning;
- no production enablement;
- no Stripe, SMS, or live scraping;
- no open/click tracking;
- no human-review bypass;
- no send-gate, suppression, compliance, billing, rate-limit, or idempotency bypass;
- no auth/RBAC/RLS/tenant-isolation change;
- no boot-guard weakening.

---

## 2. Files changed

Code/config:

- `backend/app/services/resend_webhooks.py`
- `backend/app/schemas/webhooks.py`
- `backend/app/routers/webhooks.py`
- `backend/app/main.py`
- `backend/app/observability/boot_guard.py`

Tests:

- `backend/tests/test_resend_webhooks.py`
- `backend/tests/test_router_webhooks.py`
- `backend/tests/test_resend_email_provider.py`

Docs:

- `docs/evidence/phase-3-5g-resend-webhook-verification.md`
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md`
- `docs/API_CONTRACT.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 3. Webhook verifier behavior

Added:

```text
ResendWebhookVerifier
```

Behavior:

- validates the raw request body;
- requires the Resend/Svix header set: event id, timestamp, and signature;
- verifies HMAC-SHA256 signature using an injected webhook secret;
- supports the standard `whsec_` secret encoding shape for tests/future secret resolution;
- parses JSON only after signature verification succeeds;
- returns safe controlled errors;
- does not log raw body, signature, or secret;
- does not call Resend;
- does not import Resend SDK.

Fail-closed behavior:

| Case | Result |
|---|---|
| missing injected webhook secret | `WEBHOOK_SECRET_UNAVAILABLE` / 503 |
| missing signature headers | `WEBHOOK_SIGNATURE_MISSING` / 401 |
| invalid signature | `WEBHOOK_SIGNATURE_INVALID` / 401 |
| invalid JSON after verification | `WEBHOOK_PAYLOAD_INVALID` / 400 |

Default route dependency passes no resolved secret because secret resolution is deferred. That keeps the route fail-closed in every environment until the approved secret-resolution slice.

---

## 4. Event normalization summary

Added:

```text
normalize_resend_event()
NormalizedResendWebhookEvent
ResendWebhookProcessingResult
```

Supported normalized event types:

| Resend source type | Internal type |
|---|---|
| `email.delivered` | `delivered` |
| `email.bounced` | `bounced` |
| `email.complained` | `complained` |
| `email.delivery_delayed` | `deferred` |
| `email.failed` | `failed` |
| `email.suppressed` | `suppressed` |

Ignored safely:

- `email.opened`;
- `email.clicked`;
- domain events;
- contact events;
- unknown event types.

Safe normalized fields only:

- provider;
- provider event id;
- provider message id;
- internal event type;
- occurred timestamp;
- safe metadata.

Raw webhook payloads are not persisted. Recipient, sender, subject, raw body, raw signature, and secret values are not returned in route responses or normalized event metadata.

---

## 5. Idempotency strategy

Added boundary:

```text
ResendWebhookEventStore.mark_processed(provider_event_id)
```

Added foundation store:

```text
InMemoryResendWebhookEventStore
```

Behavior:

- first-seen provider event id returns `processed`;
- duplicate provider event id returns `duplicate`;
- duplicate event ids do not create duplicate state changes in the foundation service.

No migration was added because durable webhook-event persistence is not approved yet. Future persistence should replace the store boundary with a DB-backed implementation keyed by provider + provider event id.

---

## 6. Route behavior

Added route:

```text
POST /api/v1/webhooks/resend
```

Behavior:

- does not require app user auth;
- authenticates the provider request by signature first;
- reads the raw request body before parsing;
- trusts no tenant id from the request body;
- returns only provider/status/duplicate/event type/mock-only fields;
- does not expose raw payloads or secret material;
- does not trigger real sending;
- default runtime dependency is fail-closed because secret resolution is deferred.

Example safe success response:

```json
{
  "provider": "resend",
  "status": "processed",
  "duplicate": false,
  "event_type": "delivered",
  "mock_only": true
}
```

---

## 7. Config / boot guard behavior

P3-5g preserves existing Resend live-send guard behavior and adds the webhook-specific requirement:

- if provider webhooks are enabled in production, webhook secret ref must be non-placeholder;
- if provider webhooks are enabled in staging, webhook secret ref must be non-placeholder;
- `controlled_demo` does not bypass webhook signing requirements;
- live-send guard remains intact;
- route default remains fail-closed until real secret resolution is added.

---

## 8. Tests added / updated

Added:

```text
backend/tests/test_resend_webhooks.py
backend/tests/test_router_webhooks.py
```

Updated:

```text
backend/tests/test_resend_email_provider.py
```

Coverage added:

- missing webhook secret fails closed;
- missing signature headers fail closed;
- invalid signature fails closed;
- valid signature passes verification;
- raw secret/signature/body/PII are not exposed in safe errors;
- supported Resend event types normalize correctly;
- bounce metadata keeps only safe labels;
- open/click events are ignored;
- unknown/domain/contact events are ignored;
- duplicate provider event id is idempotent;
- route is mounted;
- route default dependency fails closed;
- route verifies signature before processing;
- route returns safe normalized response;
- production boot guard blocks enabled webhooks without secret ref;
- staging boot guard blocks enabled webhooks without secret ref;
- controlled demo does not bypass webhook signing requirements;
- no Resend SDK/API/network call markers are present.

---

## 9. Local verification results

Backend:

```text
python -m ruff check app tests
python -m black --check app tests
python -m mypy app --ignore-missing-imports
python -m pytest
```

Frontend:

```text
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

Docker:

```text
docker build -f backend/Dockerfile.prod -t automatedstructure-backend:p3-5g-local backend
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:p3-5g-local frontend
```

Backend result:

```text
ruff PASS
black PASS — 209 files would be left unchanged
mypy PASS — no issues found in 154 source files
pytest PASS — 684 passed, 1 warning in 40.40s
```

Frontend result:

```text
npm ci PASS — 598 packages installed/audited
lint PASS — no ESLint warnings or errors
typecheck PASS
test PASS — 122 passed
build PASS — Next.js 14.2.35 compiled successfully, generated 27 static pages
```

Docker result:

```text
backend Docker build PASS — automatedstructure-backend:p3-5g-local, image b4fd5b6dcc4f, 260MB
frontend Docker build PASS — automatedstructure-frontend:p3-5g-local, image c39f0cb6c1d3, 158MB
```

Known warnings:

- existing FastAPI/Starlette TestClient deprecation warning;
- existing npm audit report: 10 findings;
- existing Vite CJS deprecation warning;
- expected frontend backend-unavailable fallback stderr in tests.

---

## 10. Honest limits

Still not implemented:

- real Resend outbound delivery;
- Resend SDK;
- Resend API calls;
- real webhook secret resolution from Secrets Manager;
- durable DB webhook-event storage;
- outbound message status mutation from webhook events;
- signed webhook smoke with a real Resend endpoint;
- DNS verification automation;
- internal-only real email smoke;
- external-recipient sending;
- deployment;
- registry upload;
- AWS provisioning;
- Stripe;
- SMS;
- live scraping.

---

## 11. Final verdict

P3-5g is complete as a verification, normalization, route, and idempotency-boundary foundation.

It does not enable real sending or any live provider behavior.
