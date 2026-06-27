# P3-5c — Email Provider Selection + Secrets/Config Design

**Purpose:** Define provider-selection criteria and production secrets/config design before any provider-specific adapter can be implemented.
**Status:** Docs-only plan.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `54f39e0 feat(p3-5): add email provider interface boundary`

---

## 1. Scope and hard stop

P3-5c is documentation only.

No runtime behavior changed:

- Current sending remains mock-only.
- No provider is selected as final.
- No provider credentials are available or added.
- No provider SDK is added.
- No provider API is called.
- No live adapter registry entry is added.
- Production remains disabled.
- Stripe/SMS/live scraping remain deferred.
- Send gate, manual human approval, suppression, compliance, billing, rate limits, auth/RBAC/RLS, tenant isolation, and idempotency remain mandatory.

---

## 2. Current ground truth from P3-5b

P3-5b added the provider interface boundary:

- `EmailSendProvider` Protocol.
- `ProviderSendRequest` safe request DTO.
- `ProviderSendResult` safe result DTO.
- `MockEmailSendProvider`.
- Fail-closed `EmailProviderRegistry`.
- `build_email_provider(settings)`.

Current safe config defaults:

```text
EMAIL_PROVIDER=mock
LIVE_EMAIL_SENDING_ENABLED=false
EMAIL_PROVIDER_SECRET_REF=CHANGE_ME_PLACEHOLDER
EMAIL_PROVIDER_WEBHOOK_SECRET_REF=CHANGE_ME_PLACEHOLDER
EMAIL_SENDING_DOMAIN=CHANGE_ME_PLACEHOLDER
```

Boot-guard behavior from P3-5b:

- production fails closed if `EMAIL_PROVIDER` is not `mock`;
- production fails closed if `LIVE_EMAIL_SENDING_ENABLED=true`;
- production fails closed if provider secret ref/domain config is blank or placeholder when live delivery is attempted;
- `controlled_demo` does not bypass live email delivery requirements.

---

## 3. Provider selection criteria

Evaluate each provider using the same checklist:

1. **Deliverability:** IP/domain reputation tooling, suppression support, bounce/complaint handling, dedicated/shared IP options, monitoring, and policy fit for cold outreach.
2. **API reliability:** API stability, retry semantics, provider idempotency support, rate limits, status page maturity, and historical reliability.
3. **Sandbox/test mode:** ability to test without sending to external recipients, plus safe integration smoke paths.
4. **Webhook support:** signed event callbacks for delivered/bounced/complained/deferred/opened/clicked/unsubscribed events.
5. **Suppression and complaint events:** provider-managed suppression lists, hard bounce handling, spam complaint handling, unsubscribe feedback, and export/reconciliation support.
6. **Domain authentication support:** DKIM, SPF, DMARC, return-path/bounce domain, tracking domain, and dashboard/API verification status.
7. **Cost:** monthly base, per-1,000 email cost, dedicated IP cost, validation cost, and support/deliverability add-ons.
8. **Philippines/client practicality:** ease of account opening/payment, availability from PH-based operators, support quality, and whether DNS ownership can be handled by the client or platform owner.
9. **Ease of integration:** API docs, SDK maturity, webhook docs, Terraform/IaC support, and operational simplicity.
10. **Compliance support:** opt-out/suppression tools, auditability, data retention controls, data-region options, legal/support responsiveness, and provider terms for cold outreach.

A provider must not be approved only because the API is easy. It must pass deliverability, compliance, and operations review.

---

## 4. Provider comparison

| Provider | Strengths | Risks / tradeoffs | Best fit |
|---|---|---|---|
| Amazon SES | Lowest expected unit cost, AWS-native IAM/Secrets/KMS/SNS fit, strong domain identity model, good for infra-controlled deployments. | More operational ownership; account sandbox/production access process; deliverability requires discipline; dashboard UX is less beginner-friendly than dedicated email platforms. | Internal technical smoke and cost-sensitive production once AWS ops maturity is ready. |
| SendGrid | Mature Email API, broad docs, event/webhook ecosystem, common startup/provider choice, strong dashboard. | Paid plan/support decisions matter; shared-IP reputation and compliance review must be managed; not automatically safer for cold outreach. | If owner wants a mainstream managed email platform with dashboard-first ops. |
| Postmark | Strong developer experience, clear pricing, sandbox/testing support, event webhooks, automatic suppression, DKIM/SPF/DMARC support, strong deliverability reputation. | Historically strongest for transactional email; cold outreach/broadcast use must be reviewed carefully against provider terms and message-stream policy. | If owner wants fastest safe developer workflow and high-quality ops UX for a first pilot. |
| Mailgun | Email API focus, domain-level webhooks, explicit webhook signatures, suppression/failure event support, good for technical teams. | Pricing/support tier and deliverability add-ons must be reviewed; account/domain reputation still platform-owned responsibility. | If owner wants email-API flexibility and granular webhook/event handling. |
| Resend | Modern developer experience, simple onboarding, webhooks, useful for React/email-template workflows, generous small-volume entry. | Newer ecosystem than SES/SendGrid/Postmark/Mailgun; evaluate cold outreach/provider-policy fit and advanced deliverability tooling before production. | Internal prototype/pilot if developer speed matters more than mature deliverability operations. |

### Non-final first-pilot recommendation

Recommended default for **first internal-only technical smoke**: **Amazon SES** if the production target remains AWS, because it aligns naturally with AWS Secrets Manager/KMS/IAM/SNS and keeps unit cost low.

Recommended alternate for **fastest developer/operator experience**: **Postmark**, if owner accepts its policies for the intended message stream and wants a cleaner dashboard/sandbox workflow.

This is not a final provider selection. Final provider must be owner-approved after legal/provider-terms review, DNS ownership confirmation, and internal-only smoke scope approval.

---

## 5. Secrets/config design

Future config names:

```text
EMAIL_PROVIDER=<approved provider key>
LIVE_EMAIL_SENDING_ENABLED=false by default
EMAIL_PROVIDER_SECRET_REF=<approved secret reference>
EMAIL_PROVIDER_WEBHOOK_SECRET_REF=<approved secret reference>
EMAIL_SENDING_DOMAIN=<approved sending subdomain>
EMAIL_PROVIDER_SANDBOX_MODE=true by default until smoke approval
EMAIL_DEFAULT_SENDER_IDENTITY=<approved mailbox/from identity>
EMAIL_DNS_VERIFICATION_SOURCE=<provider_api|manual_ops_record|dns_checker>
EMAIL_TENANT_DAILY_CAP=<number>
EMAIL_TENANT_HOURLY_CAP=<number>
EMAIL_CAMPAIGN_DAILY_CAP=<number>
EMAIL_MAILBOX_DAILY_CAP=<number>
EMAIL_PROVIDER_HOURLY_CAP=<number>
```

Production secret storage:

- Provider API credentials live in AWS Secrets Manager.
- Secrets are encrypted under the approved KMS key.
- App config stores only secret references, not raw values.
- Deployment role gets least-privilege read access to only required secret paths.
- Rotation must be documented before external delivery.
- `.env.example` may contain placeholders only.
- No real `.env` files are edited or committed.

Forbidden everywhere:

- raw provider API keys in DB rows;
- raw provider API keys in logs;
- raw provider API keys in audit events;
- raw provider API keys in frontend state;
- raw provider API keys in prompts or agent context;
- raw provider webhook payloads in client responses;
- raw provider response payloads in `ProviderSendResult` if they may contain PII.

Safe DB fields allowed later if approved:

- provider key;
- provider account/domain identifier;
- provider message ID;
- safe webhook event ID;
- safe provider status;
- secret reference alias/path;
- DNS verification state;
- last verification timestamp;
- safe failure code.

---

## 6. Domain/DNS design

### Sending domain

Use a dedicated outreach subdomain, not the root company domain.

Recommended pattern:

```text
outreach.<client-domain>
```

or, for internal smoke:

```text
pilot.<owned-demo-domain>
```

Do not use the same domain/subdomain for transactional product mail and cold outreach.

### Required DNS records

Provider setup must define and verify:

- SPF record or include mechanism required by provider;
- DKIM CNAME/TXT records required by provider;
- DMARC record for the visible From domain;
- bounce/return-path domain if provider requires custom return-path;
- tracking domain if open/click tracking is enabled;
- optional BIMI is out of scope unless separately approved.

### DNS workflow

1. Owner selects provider and sending domain/subdomain.
2. DNS owner confirms who can edit DNS.
3. Provider/domain records are generated in the provider dashboard or API.
4. DNS owner publishes records.
5. Backend/operator verifies records using provider dashboard/API and/or DNS checker.
6. Verification state is recorded as safe metadata.
7. Send gate must defer delivery if required DNS state is missing or failed.
8. DNS changes are rechecked before internal smoke and before any client launch.

### Ownership

Must be explicitly assigned:

- SaaS owner: approves sender/domain strategy.
- DNS owner: publishes DNS records.
- Engineering/Ops: verifies provider and backend config.
- Deliverability owner: monitors bounce/complaint/domain health.
- Legal/compliance owner: approves footer/unsubscribe copy.

---

## 7. Webhook design

### Provider event types

Future webhook ingestion should support only approved provider events:

- delivered;
- bounced/hard bounce;
- complained/spam complaint;
- deferred/temporary failure;
- opened/clicked only if tracking is approved;
- unsubscribed if the provider supports unsubscribe events.

Open/click tracking can affect privacy expectations and should remain optional until approved.

### Verification

Every webhook endpoint must:

1. identify provider by route/config;
2. load webhook signing secret via secret reference;
3. verify provider signature before parsing trusted fields;
4. reject missing/invalid signatures;
5. apply timestamp tolerance/replay defense when provider supports it;
6. never rely on unsigned event IDs or message IDs.

### Idempotency

Use provider event ID as the idempotency key:

```text
provider:<provider_key>:event:<event_id>
```

Duplicate event behavior:

- same event ID + same payload hash -> no-op replay;
- same event ID + different payload hash -> safe conflict record and no state mutation;
- missing event ID -> reject or quarantine, provider-specific.

### Tenant/message lookup

Lookup order:

1. provider message ID -> outbound message;
2. outbound message -> tenant ID/draft/campaign/contact;
3. tenant context enforced before state mutation;
4. unmatched event -> quarantine safe event record; do not guess tenant.

### Safe persistence

Persist safe normalized events only:

- event ID;
- provider key;
- outbound message ID;
- tenant ID;
- normalized event type;
- safe reason code;
- provider timestamp;
- received timestamp;
- payload hash;
- verification status.

Do not store raw webhook payload by default. If raw payload retention is required for debugging, store it only in encrypted restricted evidence storage with short retention and never expose it to frontend/client responses.

---

## 8. Owner decisions required

Before P3-5d or any provider-specific adapter implementation, owner must decide:

1. Final email provider.
2. Sending domain/subdomain.
3. DNS owner and DNS change process.
4. Webhook event scope.
5. Sandbox/test mode approval.
6. Internal-only real-send smoke approval.
7. Daily/hourly caps by tenant, campaign, mailbox, and provider.
8. Default sender identity.
9. Legal footer and unsubscribe copy.
10. Deliverability monitor owner.
11. Incident response owner.
12. Whether open/click tracking is allowed.
13. Whether provider-managed unsubscribe links are used or app-owned unsubscribe is required.
14. Whether provider suppression lists must sync into app suppression records.

No provider adapter should be implemented until at least provider, domain, DNS owner, secret path, and sandbox/internal smoke scope are approved.

---

## 9. Implementation slice plan

Recommended future sequence:

### P3-5d — Provider-specific adapter skeleton after provider choice

Add provider-specific adapter module and tests only after provider choice. Keep sandbox/live disabled by default. No external send until later smoke approval.

### P3-5e — Webhook verification design/implementation if approved

Add signed webhook route, provider event normalization, idempotency, safe event persistence, and quarantine path.

### P3-5f — Sandbox/test-provider smoke if approved

Use provider sandbox/test mode only. Verify no external recipients are contacted. Record evidence.

### P3-5g — Internal-only real-send smoke if approved

Send to owner-approved internal address/domain only. Verify gate chain, provider ID, webhook events, audit logs, no secret leakage, and rollback/pause path.

### P3-5h — Evidence + launch blocker update

Record provider decision, DNS proof, secret refs, smoke results, remaining launch blockers, and no-go conditions.

---

## 10. Tests needed

Future tests:

- provider config missing fails boot;
- provider secret ref required;
- sending domain required;
- sandbox mode cannot send externally unless approved;
- webhook signature required;
- invalid webhook signature rejected;
- unknown event ignored, rejected, or quarantined safely;
- duplicate webhook event idempotent;
- duplicate event ID with mismatched payload hash does not mutate state;
- bounce updates safe message state;
- complaint updates safe message state and suppression;
- delivery updates safe message state;
- deferred event does not mark final failure prematurely;
- unmatched provider message ID quarantines safely;
- no raw secrets in logs/audit/client responses;
- no raw webhook payload in client responses;
- no real provider call in unit tests;
- sandbox/integration tests require explicit opt-in marker.

---

## 11. Source notes checked for provider comparison

Official provider pages checked on 2026-06-28:

- Amazon SES pricing and SES identity verification docs.
- Twilio SendGrid product/pricing page.
- Postmark pricing and webhook docs.
- Mailgun pricing and webhook docs.
- Resend pricing page.

Provider prices/features change. Re-check official provider docs before final owner decision or procurement.

---

## 12. Final verdict

P3-5c provider-selection and secrets/config design is complete.

Blocked before provider adapter implementation:

- final provider;
- sending domain/subdomain;
- DNS owner;
- webhook event scope;
- sandbox/test mode approval;
- internal-only smoke approval;
- caps;
- default sender identity;
- legal footer/unsubscribe copy;
- deliverability owner;
- incident response owner.
