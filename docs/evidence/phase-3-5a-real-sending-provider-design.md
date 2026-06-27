# P3-5a — Real Sending / Provider Design Inspection + Stop-Gate Plan

**Purpose:** Inspect the current mock sending lane and design the future real-provider lane without enabling live delivery.
**Status:** Docs-only inspection and plan.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `8657cbf docs(p3-4): accept rate limit abuse protection green pass`

---

## 1. Scope and hard stop

P3-5a is design-only. It does not implement provider code, does not add credentials, does not call any provider API, and does not change runtime config.

Hard stop still holds:

- Production remains disabled.
- No deployment was performed.
- Live email delivery remains disabled.
- Provider integrations remain deferred.
- Stripe remains deferred.
- SMS remains deferred.
- Live scraping remains deferred.
- Manual human approval remains required before any future live cold-email send.
- Send gate, human approval, suppression, compliance, billing, rate limits, auth/RBAC/RLS, tenant isolation, and idempotency must not be bypassed.

---

## 2. Inspection notes

Inspected requested surfaces:

- `backend/app/routers/sending.py`
- `backend/app/services/send_gate.py`
- `backend/app/services/mock_sender.py` (current send-intent implementation; `services/send_intent.py` does not exist)
- `backend/app/services/deliverability.py`
- `backend/app/services/compliance.py`
- `backend/app/services/compliance_api.py` (suppression API facade; `services/suppressions.py` does not exist)
- `backend/app/repositories/sending_repo.py` (current outbound-message repository; `repositories/outbound_message_repo.py` does not exist)
- `backend/app/models/sending.py` (current outbound-message model; `models/outbound_message.py` does not exist)
- `backend/app/models/compliance.py` (suppression + compliance profile models; `models/suppression.py` and `models/compliance_profile.py` do not exist as separate files)
- `backend/app/models/billing.py` (contains `TenantSubscription`; `models/tenant_subscription.py` does not exist)
- `backend/app/observability/boot_guard.py`
- `backend/app/config.py`
- `backend/tests/test_router_sending.py`
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md`
- `docs/API_CONTRACT.md`
- `docs/ARCHITECTURE.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/evidence/phase-3-4f-rate-limit-abuse-protection-acceptance.md`

---

## 3. Current sending state

### Mock-only behavior

Current send-intent flow is local/mock-only:

- `POST /api/v1/send-gate/dry-run` evaluates gates and never sends.
- `POST /api/v1/send-intents` is wired to `MockSenderService`.
- `MockSenderService` creates local `outbound_messages` rows with `mock_sent` or `blocked` status only.
- `SendIntentResponse` / `MockSendResult` include `mock_only=True`.
- Deliverability metrics are deterministic mock calculations from local rows, not provider events.
- Mailbox health is deterministic mock data (`mock-<tenant>.example.com`) and performs no DNS/provider calls.
- Compliance profile API explicitly rejects `live_sending_allowed=True` with `LIVE_SENDING_DEFERRED`.
- SMS enablement is rejected with `SMS_COMPLIANCE_DEFERRED`.
- No live adapter, provider registry entry, worker provider call, webhook handler, DNS verifier, or secret loader for email delivery exists.

### Gates that already exist

Current `SendGateService.evaluate_gate()` enforces:

1. RBAC permission: `CAN_SCHEDULE_SEND`.
2. Billing feature: `CAN_SEND` through centralized billing gates.
3. Draft existence, tenant match, and object authorization.
4. Draft status constraint.
5. Review queue approval; non-approved review blocks send.
6. Draft/review/campaign/contact tenant consistency.
7. Suppression check through `ComplianceGateService.is_suppressed()`.
8. Safety gates: prompt injection, source trust, groundedness, failure/missing checks.
9. Duplicate outbound-message check.
10. Tenant send rate-limit check.
11. Send-gate result record + audit event.

Router-level P3-4 endpoint limits are also wired on dry-run and send-intent routes.

### DB records that exist

Current records/models include:

- `send_gate_results`: `passed` or `denied`, with deny reason codes.
- `outbound_messages`: statuses are `mock_queued`, `mock_sent`, `blocked`, `duplicate`.
- `compliance_profiles`: `jurisdiction`, `sending_review_required`, `live_sending_allowed`, `sms_allowed`.
- `suppressions`: `tenant_id`, `channel`, hashed contact identifier, reason/source, never-contact flag, revoke timestamp.
- `tenant_subscriptions`: mock billing state and plan link.
- `idempotency_keys`: route-level idempotency for send gate and send intent flows.
- `audit_events`: gate pass/fail and outbound-message events.

### Missing for live provider delivery

Required before any provider delivery implementation:

- Provider-neutral email sending interface.
- Mock adapter and future real adapter boundary.
- Adapter registry that is fail-closed and does not expose live adapters unless explicitly configured.
- Provider selection and owner decision.
- Secret reference model/config, without raw credentials in DB/logs/frontend.
- Mailbox/domain configuration model or approved config path.
- Provider message ID fields and event/status model additions.
- Provider idempotency key strategy.
- Provider failure state and retry/reconciliation rules.
- Bounce/complaint/open/reply webhook ingestion design and signed verification.
- DNS/SPF/DKIM/DMARC verification path.
- Unsubscribe/footer/legal copy enforcement before provider call.
- Production boot guard rules for provider config completeness.
- Internal-only provider sandbox smoke plan.

---

## 4. Real provider architecture plan

### Provider interface shape

Future interface should be protocol-based and narrow:

```python
class EmailSendProvider(Protocol):
    kind: str

    async def send_email(
        self,
        *,
        tenant_id: UUID,
        message_id: UUID,
        idempotency_key: str,
        from_mailbox: MailboxIdentity,
        recipient: RecipientIdentity,
        content: EmailContent,
        metadata: ProviderMetadata,
    ) -> ProviderSendResult: ...
```

Result shape:

```python
@dataclass(frozen=True)
class ProviderSendResult:
    provider: str
    provider_message_id: str | None
    status: Literal["accepted", "deferred", "failed"]
    safe_error_code: str | None = None
    retry_after_seconds: int | None = None
```

The provider contract must not accept or return raw credentials. It must return safe provider metadata only.

### Adapter registry

Future registry should be config-driven and fail-closed:

- `mock_email` adapter is always allowed only in local/development/demo/mock-safe paths.
- real adapters are not registered unless a future approved config flag and secret reference are both valid.
- unknown provider key fails boot or fails request with a safe provider-unavailable error.
- registry must not import provider SDKs unless a real adapter is selected.
- tests must prove no live adapter is active by default.

### Mock adapter vs real adapter boundary

Mock adapter:

- never performs network calls;
- returns deterministic provider-like result;
- preserves idempotency/status/audit behavior;
- safe in local/demo;
- clearly marks `mock_only=True`.

Real adapter:

- only available after owner approval and config/secrets are present;
- performs provider API call after all send gates pass;
- uses provider idempotency key when available;
- returns provider message ID/status;
- never logs body, tokens, API keys, raw SMTP credentials, or sensitive headers;
- records safe failure state if provider call fails.

### Provider choices to decide later

Owner must choose provider later. Candidate categories:

- AWS SES for infrastructure-controlled sending.
- SendGrid/Mailgun/Postmark/Resend-style API provider for managed email delivery.
- SMTP relay only if it supports safe idempotency/reconciliation and approved monitoring.

No provider is selected in P3-5a.

### Secret reference pattern

Use secret references, not raw secrets:

```text
provider_credentials_secret_ref = aws-secrets-manager path or approved secret alias
provider_webhook_secret_ref = aws-secrets-manager path or approved secret alias
```

Rules:

- no raw provider API key in DB;
- no raw provider API key in `.env.example` beyond placeholders;
- no raw provider secret in logs/audit/client responses;
- frontend never receives provider credentials;
- DB may store provider kind, mailbox/domain IDs, safe message IDs, and secret references only if approved.

---

## 5. Required send safety chain

Future real-provider flow must be strictly ordered:

1. Authenticate user/session through Clerk-backed auth.
2. Confirm tenant membership, RBAC, object authorization, and tenant context.
3. Billing gate: `is_active(tenant)` and `has_feature(tenant, CAN_SEND)`.
4. Compliance profile exists and is approved for live email delivery.
5. Suppression/unsubscribe check blocks suppressed recipients.
6. Contact/list verification blocks invalid/disposable/bounced/suppressed recipients.
7. Review item must be manually approved for first real client policy.
8. Prompt-injection, source-trust, and groundedness gates must pass.
9. Human edits must be re-grounded before delivery.
10. Send gate must pass and record `send_gate_results`.
11. Rate limits: route, tenant, campaign, mailbox, and provider caps.
12. Idempotency/duplicate-send lock acquired before provider call.
13. Provider adapter sends only after all gates pass.
14. Outbound message record stores safe provider status and provider message ID.
15. Audit/log/event tracking records safe metadata only.
16. Provider webhook/status reconciliation updates outcome/deliverability state after signed verification.

No agent, frontend button, n8n workflow, reviewer action, provider callback, or worker may bypass this chain.

---

## 6. Owner decisions required before implementation

Before any real-provider implementation beyond design-only code, owner must decide:

1. Email provider choice.
2. Sending domain/subdomain.
3. DNS ownership and who updates SPF/DKIM/DMARC/PTR/tracking-domain records.
4. Mailbox/warm-up policy and allowed sender identities.
5. Daily/hourly tenant limits, campaign limits, mailbox limits, and provider caps.
6. Manual approval policy confirmation for first client.
7. Unsubscribe footer, physical address, legal copy, and outreach wording.
8. Pilot client domain or internal demo domain for first smoke.
9. Who owns deliverability monitoring and pause decisions.
10. Provider webhook/event scope: bounces, complaints, deliveries, opens, clicks, replies.
11. Whether sandbox/test-provider mode is allowed before live-domain smoke.
12. Incident response owner for duplicate sends, provider outage, spam complaint, bounce spike, and secret exposure.

Current resolved decision that still holds: first real client cold-email drafts require manual human approval.

---

## 7. Required production/provider config

Future implementation must add config/secrets only through approved paths:

- provider kind, e.g. `EMAIL_PROVIDER=<approved provider key>`;
- provider credentials secret reference;
- sending domain/subdomain;
- default from mailbox identity;
- provider webhook signing secret reference if inbound provider events are used;
- DNS verification status source;
- tenant/campaign/mailbox/provider rate caps;
- live-delivery feature flag defaulting disabled;
- provider sandbox/test mode flag if approved.

Boot guard must fail closed in production/staging if live email delivery is selected and any required config is missing or placeholder:

- provider kind not approved;
- credentials secret reference missing;
- domain authentication incomplete;
- webhook signing secret missing when webhooks are enabled;
- compliance profile not approved for tenant;
- manual approval policy disabled for first client;
- Redis rate-limit backend missing;
- mock adapter selected without an approved controlled-demo exception.

---

## 8. Implementation slice plan

Recommended sequence:

### P3-5b — Provider interface + mock/live boundary hardening

Design-only code boundary if approved. Add provider Protocols, result DTOs, mock adapter parity, registry skeleton, and fail-closed config selectors. No real provider SDK, no network calls, no live adapter registry entry.

### P3-5c — Provider selection + secrets config design

After owner chooses provider. Add config names, secret reference validation, boot-guard checks, and documentation. Still no provider calls unless explicitly approved.

### P3-5d — Sandbox/test-provider integration

Only if approved. Add one adapter using provider sandbox/test mode or internal-only credentials. No external customer sends. Webhook signing verification if used.

### P3-5e — Internal-only real send smoke

Only if approved. Send to a controlled internal address/domain. Must verify gates, idempotency, provider response, outbound record, audit, and no leakage.

### P3-5f — Evidence + launch-blocker update

Record provider config, smoke results, safety checks, owner decisions, and remaining legal/provider launch blockers.

---

## 9. Tests needed

Required future tests:

- real provider path disabled by default;
- production boot fails if provider config is incomplete;
- mock adapter remains the default in safe local/mock contexts;
- live adapter cannot be registered without approved config;
- human approval required before provider send;
- suppression blocks provider send;
- compliance profile blocks provider send;
- rate limit blocks provider send;
- billing gate blocks provider send;
- send gate cannot be bypassed by worker/router/provider callback;
- duplicate send/idempotency prevents second provider call;
- provider failure records safe failed/deferred state;
- unknown provider result triggers safe reconciliation path before retry;
- webhook signature required before provider event ingestion;
- no raw secrets, tokens, email bodies, provider payloads, or raw API errors in logs/audit/client responses;
- no live provider call in unit tests;
- sandbox/integration tests require explicit opt-in marker and safe internal target only.

---

## 10. Final verdict

Docs-only inspection was required first and is complete.

Safe next step: implement design-only provider interface / mock-live boundary hardening in P3-5b **only if owner accepts this plan**.

Blocked before any real provider delivery: provider choice, domain/DNS ownership, legal copy, compliance approval, warm-up/caps, secrets path, webhook signing decision, deliverability owner, and internal-only smoke approval.
