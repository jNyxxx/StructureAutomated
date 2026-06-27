# P3-5d — Real Sending Owner Decision Packet

**Purpose:** Collect explicit owner decisions required before any real sending implementation can begin.
**Status:** Owner decision packet — blocked until answered.
**Date:** 2026-06-28 (Asia/Manila)
**Base commit:** `0630c29 docs(p3-5): plan provider selection and secrets config`

---

## 1. Strong stop warning

Real sending implementation must not proceed on assumptions.

Until this packet is answered and recorded:

- Do not add a real provider adapter.
- Do not add provider SDKs.
- Do not add provider credentials.
- Do not edit real `.env` files.
- Do not call provider APIs.
- Do not add live adapter registry entries.
- Do not enable live email sending.
- Do not enable production.
- Do not bypass send gate, manual approval, suppression, compliance, billing, rate limits, auth/RBAC/RLS, tenant isolation, or idempotency.
- Do not enable Stripe, SMS, or live scraping.
- Do not deploy anything.

---

## 2. Current system status

Current Phase 3 real-sending lane status:

- P3-5a provider/sending lane design is complete.
- P3-5b provider interface + mock/live boundary is complete.
- P3-5c provider selection + secrets/config design is complete.
- Current sending remains mock-only.
- No real provider has been selected.
- No provider credentials are available.
- No live adapter has been added.
- No provider SDK has been added.
- Production is not enabled.
- Stripe/SMS/live scraping remain deferred.

---

## 3. What is already safe / green

Already completed and safe:

- Provider-neutral `EmailSendProvider` Protocol exists.
- Safe `ProviderSendRequest` / `ProviderSendResult` DTOs exist.
- Network-free `MockEmailSendProvider` exists.
- Adapter registry fails closed for live provider names.
- Default config remains `EMAIL_PROVIDER=mock` and `LIVE_EMAIL_SENDING_ENABLED=false`.
- Production boot guard rejects non-mock provider / live sending in the current build.
- Mock sender calls provider boundary only after send gate passes.
- Send gate still enforces review approval, billing, suppression, safety, duplicate checks, and rate limits before provider boundary.
- P3-5c defines secret-ref-only design and AWS Secrets Manager/KMS production path.

---

## 4. What remains blocked

Blocked until owner answers this packet:

- final email provider;
- exact sending domain/subdomain;
- DNS owner and propagation/verifier owner;
- sender identity;
- legal footer / unsubscribe copy;
- send caps;
- sandbox/test mode approval;
- internal-only real email smoke approval;
- internal recipient address for smoke;
- webhook event scope;
- deliverability monitoring owner;
- incident/emergency-stop owner;
- provider account owner.

---

## 5. Owner decision packet

### 5.1 Email provider

Choose one:

- [ ] Amazon SES
- [ ] Postmark
- [ ] SendGrid
- [ ] Mailgun
- [ ] Resend
- [ ] Other: ______________________________

Recommended default for first internal-only smoke:

- Amazon SES if AWS remains the target deployment platform.

Owner decision:

```text
Approved provider:
Reason:
Approval date:
Approver:
```

### 5.2 Sending domain / subdomain

Example:

```text
outreach.automatedstructure.com
```

Owner must confirm exact value:

```text
Approved sending domain/subdomain:
Root domain owner:
Can this domain be used for cold outreach? yes/no
Can this domain be isolated from transactional product email? yes/no
```

### 5.3 DNS owner

Who will add and confirm DNS records?

Required DNS work:

- SPF;
- DKIM;
- DMARC;
- bounce / return-path records if provider requires them;
- tracking domain records if tracking is approved.

Owner fill-in:

```text
DNS owner name/team:
DNS provider/registrar:
Who adds records:
Who confirms propagation:
Who confirms provider dashboard/API verification:
Expected DNS change window:
```

### 5.4 Sender identity

Owner fill-in:

```text
Default From name:
Default From email:
Reply-to email:
Bounce / return-path handling owner:
Mailbox/account owner:
Allowed sender identities:
Disallowed sender identities:
```

Rules:

- Default sender identity must align with approved sending domain.
- Reply-to must route to a monitored inbox.
- Bounce/return-path handling must be provider-supported and monitored.

### 5.5 Legal / unsubscribe copy

Owner fill-in:

```text
Required footer text:
Company / physical mailing address if required:
Unsubscribe wording:
Unsubscribe handling: provider-managed / app-managed / both
Compliance reviewer:
Compliance approver:
Approval date:
```

Minimum requirement:

- Every first real-client AI-generated cold email still requires manual human approval.
- Legal copy must be approved before sandbox-to-real smoke.
- Unsubscribe must not be optional once external delivery is approved.

### 5.6 Send caps

Owner fill-in:

```text
Tenant hourly cap:
Tenant daily cap:
Campaign daily cap:
Mailbox daily cap:
Provider hourly cap:
First pilot cap:
```

Recommendation for first pilot:

```text
Internal-only smoke: 1 approved recipient, 1 approved email.
First external pilot after separate approval: start extremely conservative, e.g. 5-10/day per mailbox, then ramp only if bounce/complaint/DNS health stays green.
```

### 5.7 Sandbox / internal smoke

Owner fill-in:

```text
Sandbox/test mode approved? yes/no
Provider sandbox mode to use:
One internal-only real email smoke approved? yes/no
Allowed internal recipient address:
Allowed sender identity for smoke:
Who approves smoke result:
Smoke success criteria:
Emergency rollback/stop owner:
```

Hard rule:

- No external recipient smoke unless separately approved after internal smoke evidence is green.

### 5.8 Webhook scope

Choose approved event scope:

- [ ] delivered
- [ ] bounced
- [ ] complained
- [ ] deferred
- [ ] unsubscribed
- [ ] opened/clicked

Opened/clicked tracking:

```text
Open tracking approved? yes/no
Click tracking approved? yes/no
Reason / privacy approval:
```

Webhook security:

```text
Webhook signing required? yes/no
Webhook signing secret owner:
Webhook endpoint exposure approved? yes/no
Webhook replay window/tolerance:
```

Default recommendation:

- Require webhook signing.
- Start with delivery, bounce, complaint, deferred, and unsubscribe events.
- Keep open/click tracking disabled unless explicitly approved.

### 5.9 Deliverability owner

Owner fill-in:

```text
Deliverability monitor owner:
Backup owner:
Monitoring cadence:
Who watches bounce rate:
Who watches complaint rate:
Who watches provider blocks:
Who watches warm-up:
Who watches DNS/domain health:
Who can pause a mailbox/domain:
```

Minimum monitoring before any external delivery:

- bounce rate;
- complaint rate;
- provider rejected/deferred rates;
- DNS auth status;
- warm-up state;
- suppression/unsubscribe changes.

### 5.10 Incident owner

Owner fill-in:

```text
Emergency stop owner:
Backup stop owner:
Who owns provider account access:
Who can rotate provider secrets:
Who can pause all sends:
Who communicates incident status:
Who approves resume after incident:
```

Emergency-stop triggers:

- duplicate live send detected;
- unexpected external recipient contacted;
- provider credential exposure suspected;
- bounce rate crosses approved threshold;
- spam complaint crosses approved threshold;
- DNS/domain authentication fails;
- provider account is warned, blocked, or suspended;
- webhook signature verification fails repeatedly;
- app sends without approved manual review;
- tenant isolation or RBAC issue suspected.

---

## 6. What implementation starts only after approval

Only after this packet is answered and approved may the team start:

1. Provider-specific adapter skeleton.
2. Provider-specific config validation.
3. Secret-ref wiring to approved secrets backend.
4. Domain/DNS verification implementation.
5. Signed webhook endpoint implementation.
6. Sandbox/test-provider smoke.
7. Internal-only real email smoke.

Even after approval, implementation must preserve:

- mock disabled/live disabled defaults;
- fail-closed boot guard;
- send gate before provider call;
- manual human approval;
- suppression/compliance/billing/rate-limit checks;
- idempotency and duplicate-send prevention;
- no raw secrets or raw provider payloads in logs/audit/frontend/client responses.

---

## 7. Required approval signature

Owner must complete:

```text
Provider approved:
Sending domain approved:
DNS owner approved:
Sender identity approved:
Legal/unsubscribe copy approved:
Caps approved:
Sandbox mode approved:
Internal-only smoke approved:
Webhook scope approved:
Deliverability owner approved:
Incident owner approved:

Owner name:
Owner role:
Approval date:
Notes / restrictions:
```

---

## 8. Final verdict

P3-5d is complete as a decision packet.

The real sending lane remains blocked until the owner answers this packet.
