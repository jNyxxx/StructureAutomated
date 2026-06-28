# P3-5f — Resend Adapter Skeleton

**Purpose:** Add a Resend adapter skeleton behind the existing email-provider boundary while keeping live sending unreachable.
**Status:** Complete.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `b82864a ci(p3-7): add validation gates without deployment`

---

## 1. Scope and hard stop

P3-5f adds code/tests for a disabled Resend skeleton and fail-closed config behavior only.

Confirmed not done:

- no live email delivery;
- no Resend network call;
- no provider SDK added;
- no real credentials added;
- no real environment file edit;
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

## 2. Files changed

Code/config:

- `backend/app/services/email_provider.py`
- `backend/app/config.py`
- `backend/app/observability/boot_guard.py`
- `.env.example`

Tests:

- `backend/tests/test_resend_email_provider.py`

Docs:

- `docs/evidence/phase-3-5f-resend-adapter-skeleton.md`
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

---

## 3. Resend adapter skeleton summary

Added:

```text
ResendEmailSendProvider
```

Behavior:

- implements the existing `EmailSendProvider` contract;
- uses the existing `ProviderSendRequest` / `ProviderSendResult` boundary shapes;
- imports no provider SDK;
- performs no outbound call;
- resolves no secret values;
- stores no raw provider payload;
- raises a safe controlled error on every send attempt:

```text
LIVE_EMAIL_PROVIDER_DISABLED
```

This makes Resend visible as a provider direction without making it capable of delivering email.

---

## 4. Provider registry behavior

Default remains unchanged:

```text
EMAIL_PROVIDER=mock
LIVE_EMAIL_SENDING_ENABLED=false
```

Registry behavior after P3-5f:

| Config | Behavior |
|---|---|
| `mock` + live disabled | Resolves mock provider. |
| `mock` + live enabled | Fails closed. |
| unknown provider | Fails closed. |
| `resend` + live disabled | Resolves disabled Resend skeleton; send attempts fail closed. |
| `resend` + live enabled + incomplete config | Fails closed during provider build. |
| `resend` + live enabled + complete config | Resolves disabled Resend skeleton; send attempts still fail closed in P3-5f. |

No silent fallback from Resend to mock exists.

---

## 5. Config / boot guard behavior

Added safe config fields:

```text
EMAIL_PROVIDER_WEBHOOKS_ENABLED
EMAIL_TENANT_HOURLY_CAP
EMAIL_TENANT_DAILY_CAP
EMAIL_CAMPAIGN_DAILY_CAP
EMAIL_MAILBOX_DAILY_CAP
```

`.env.example` contains placeholders/default caps only. No real environment file changed.

Boot guard behavior:

- production still gets the full boot guard;
- staging now also gets email-provider live-send guard checks;
- unknown provider names fail closed;
- live sending requires the approved Resend provider key;
- live Resend config requires non-placeholder secret refs/domain and positive caps;
- webhook secret ref is required when webhook handling is enabled;
- `controlled_demo` does not bypass Resend live-send requirements.

---

## 6. Send path safety confirmation

Existing send path remains preserved:

- `POST /api/v1/send-intents` response shape remains stable;
- default mock send path still works;
- `MockSenderService` still evaluates send gate before provider call;
- gate failures still block before provider call;
- idempotency replay still prevents provider calls;
- suppression/compliance/billing/rate-limit/duplicate-send checks remain upstream of provider send;
- Resend skeleton cannot send even if resolved.

---

## 7. Tests added / updated

Added:

```text
backend/tests/test_resend_email_provider.py
```

Coverage added:

- default provider remains mock;
- Resend does not silently fallback to mock;
- Resend skeleton is disabled when live flag is off;
- live Resend with missing secret ref fails closed;
- live Resend with placeholder secret ref fails closed;
- live Resend with missing domain fails closed;
- live Resend with missing caps fails closed;
- webhook secret required when webhook handling is enabled;
- complete Resend config still resolves only to disabled skeleton;
- disabled skeleton error does not expose secret refs, sending domain, or recipient refs;
- Resend skeleton source has no network/provider SDK markers;
- production boot guard blocks unsafe Resend config;
- staging live-send guard blocks unsafe Resend config;
- controlled demo does not bypass Resend boot guard.

Existing P3-5b tests still prove send-intent blocks before provider when gates fail and mock path remains unchanged.

---

## 8. Backend gate results

Command:

```text
python -m ruff check app tests
python -m black --check app tests
python -m mypy app --ignore-missing-imports
python -m pytest
```

Result:

```text
ruff PASS
black PASS — 204 files would be left unchanged
mypy PASS — no issues found in 151 source files
pytest PASS — 659 passed, 1 warning in 41.19s
```

Known warning:

- existing FastAPI/Starlette TestClient deprecation warning.

---

## 9. Frontend gate results

Command:

```text
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

Result:

```text
npm ci PASS — 598 packages installed/audited
lint PASS — no ESLint warnings or errors
typecheck PASS
test PASS — 122 passed
build PASS — Next.js 14.2.35 compiled successfully, generated 27 static pages
```

Known notes:

- existing npm audit report: 10 findings;
- no audit fix was run;
- existing Vite CJS deprecation warning;
- expected backend-unavailable fallback stderr in frontend tests.

---

## 10. Docker build results

Command:

```text
docker build -f backend/Dockerfile.prod -t automatedstructure-backend:p3-5f-local backend
docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:p3-5f-local frontend
```

Result:

```text
backend Docker build PASS
frontend Docker build PASS
```

Local validation images:

```text
automatedstructure-backend:p3-5f-local    9317d5275c44    260MB
automatedstructure-frontend:p3-5f-local   c39f0cb6c1d3    158MB
```

No image registry upload was performed.

---

## 11. Honest limits

Still not implemented:

- real Resend delivery;
- Resend provider SDK;
- Resend outbound call;
- signed Resend webhook endpoint;
- DNS verification automation;
- internal-only real email smoke;
- external-recipient sending;
- deployment;
- registry upload;
- AWS provisioning;
- Stripe;
- SMS;
- live scraping.

The next Resend slice remains blocked on the pre-smoke values from P3-5e and separate owner approval.

---

## 12. Final verdict

P3-5f is complete.

Resend now exists as a disabled, fail-closed adapter skeleton behind the provider boundary. Default mock behavior is preserved, send safety gates remain upstream, and no live-provider behavior is reachable.
