# P3-5b — Provider Interface + Mock/Live Boundary Hardening

**Purpose:** Add a provider abstraction and fail-closed mock/live boundary without adding real provider adapters or enabling live delivery.
**Status:** Complete and ready to commit.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `5cd9406 docs(p3-5): plan real sending provider lane`

---

## 1. Scope

P3-5b is architecture hardening only. It adds the provider boundary needed for future real sending while preserving mock-only runtime behavior.

Hard stops held:

- No real sending enabled.
- No real provider selected.
- No provider SDK added.
- No real provider credentials added.
- No provider API call made.
- No live adapter registry entry added.
- Production not enabled.
- Stripe/SMS/live scraping remain deferred.
- No deployment performed.
- Send gate, manual human approval, suppression, compliance, billing, rate limits, auth/RBAC/RLS, tenant isolation, and idempotency were not bypassed.

---

## 2. Provider interface added

Created `backend/app/services/email_provider.py`.

Added:

- `EmailSendProvider` Protocol.
- `ProviderSendRequest` safe request DTO.
- `ProviderSendResult` safe result DTO.
- `EmailProviderRegistry` fail-closed resolver.
- `MockEmailSendProvider` network-free mock adapter.
- `build_email_provider(settings)` factory.

`ProviderSendRequest` intentionally carries safe identifiers/references only in this slice:

- tenant ID
- draft ID
- idempotency key
- requested timestamp
- channel
- recipient/content references
- safe metadata

It does **not** include provider credentials.

`ProviderSendResult` includes only safe provider result fields:

- provider key
- provider message ID
- provider status: `accepted`, `deferred`, or `failed`
- accepted timestamp
- optional raw provider response reference
- safe metadata
- safe error code/message

Raw provider payloads are not stored in the result DTO because they may contain PII.

---

## 3. Mock adapter boundary

`MockEmailSendProvider` is the only registered adapter.

Behavior:

- returns deterministic `accepted` provider result;
- uses `provider="mock"`;
- produces a deterministic mock provider message ID from the draft ID;
- returns safe metadata only;
- performs no network calls;
- imports no provider SDKs.

`MockSenderService` now calls the configured `EmailSendProvider` only after `SendGateService.evaluate_gate()` passes.

Existing API response shapes remain unchanged:

- `POST /api/v1/send-intents` still returns the existing mock-only response DTO.
- `mock_only=True` behavior is preserved.
- `outbound_messages` still uses existing mock statuses; no migration/schema change was introduced.

---

## 4. Adapter registry fail-closed behavior

`EmailProviderRegistry` resolves only:

```text
provider_key=mock + live_enabled=false -> MockEmailSendProvider
```

Fail-closed cases:

- unknown provider key -> `503 EMAIL_PROVIDER_NOT_AVAILABLE`;
- live provider name (`sendgrid`, `postmark`, `ses`, `mailgun`, `smtp`, etc.) -> fail closed;
- `provider_key=mock` with `live_enabled=true` -> `503 LIVE_EMAIL_PROVIDER_NOT_IMPLEMENTED`;
- no live provider silently falls back to mock.

No live provider adapter is registered in this slice.

---

## 5. Config and boot-guard behavior

Added safe config fields to `Settings`:

```text
email_provider = "mock"
live_email_sending_enabled = false
email_provider_secret_ref = None
email_provider_webhook_secret_ref = None
email_sending_domain = None
```

Updated `.env.example` with placeholders only:

```text
EMAIL_PROVIDER=mock
LIVE_EMAIL_SENDING_ENABLED=false
EMAIL_PROVIDER_SECRET_REF=CHANGE_ME_PLACEHOLDER
EMAIL_PROVIDER_WEBHOOK_SECRET_REF=CHANGE_ME_PLACEHOLDER
EMAIL_SENDING_DOMAIN=CHANGE_ME_PLACEHOLDER
```

No real `.env` file was edited.

Production boot guard now fails closed when:

- `EMAIL_PROVIDER` is not `mock`, because this build has no approved live adapter;
- `LIVE_EMAIL_SENDING_ENABLED=true`, because live delivery is not approved/implemented in this slice;
- live sending is enabled and provider secret ref/domain are blank or placeholders.

`controlled_demo` does not bypass live email-sending requirements.

---

## 6. Send safety chain confirmation

Existing send safety chain remains intact:

1. Authenticated principal required.
2. RBAC permission required.
3. Billing `CAN_SEND` gate required.
4. Draft/object tenant authorization required.
5. Draft status constraints enforced.
6. Manual review approval required.
7. Draft/review/contact tenant consistency required.
8. Suppression check enforced.
9. Safety gates required: prompt injection, source trust, groundedness.
10. Duplicate send check enforced.
11. Tenant send rate limit enforced.
12. Send-gate result and audit are recorded.
13. Provider boundary is called only after gates pass.
14. Provider failure records a safe blocked outbound state and safe audit details.
15. Idempotency replay does not call the provider.

No route, service, worker, UI path, or provider boundary bypasses send gate or manual approval.

---

## 7. Tests added/updated

Created:

- `backend/tests/test_email_provider.py`
- `backend/tests/test_mock_sender_provider_boundary.py`

Updated:

- `backend/tests/test_boot_guard.py`
- `backend/tests/test_router_sending.py`

Test coverage added:

- default provider resolves to mock;
- mock adapter returns expected safe result;
- mock adapter source contains no network/provider SDK calls;
- unknown/live provider names fail closed;
- mock provider with live sending enabled fails closed;
- factory does not silently fall back from live provider to mock;
- production boot guard rejects non-mock provider;
- production boot guard rejects live email sending in this build;
- production live email sending requires secret ref and sending domain;
- `controlled_demo` does not bypass live email boot-guard requirements;
- provider send happens only after gate pass;
- gate failure blocks before provider send;
- provider failure records safe blocked state;
- idempotency replay prevents provider send;
- sending router DI uses mock provider by default;
- sending router source does not import provider SDKs.

---

## 8. Gate results

Focused gate before docs:

```text
python -m ruff check app tests
PASS

python -m black --check app tests
PASS

python -m mypy app --ignore-missing-imports
PASS

python -m pytest -q tests/test_email_provider.py tests/test_mock_sender_provider_boundary.py tests/test_boot_guard.py tests/test_router_sending.py tests/test_send_gate.py
PASS
```

Full green-pass gates are recorded in the final task output.

---

## 9. Honest limits

Still true after P3-5b:

- No real provider selected.
- No provider SDK added.
- No real credentials added.
- No production enabled.
- No real sending enabled.
- No live adapter registry entry added.
- No real provider API call made.
- No Stripe enabled.
- No SMS enabled.
- No live scraping enabled.
- No deployment performed.

---

## 10. Safe next slice

P3-5b is ready to commit after full gates pass.

Next safe slice after owner acceptance:

- P3-5c provider selection + secrets/config design, still no live sending unless explicitly approved.

Still blocked before any real provider delivery:

- provider choice;
- sending domain/DNS ownership;
- legal copy/unsubscribe footer;
- compliance approval;
- warm-up/caps;
- approved secret path;
- webhook signing decision;
- deliverability owner;
- internal-only smoke approval.
