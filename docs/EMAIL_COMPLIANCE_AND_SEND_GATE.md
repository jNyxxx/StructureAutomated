# Email Compliance & Send Gate

**Purpose:** The final server-side send gate, no-send reason codes, compliance profile, suppression/unsubscribe, duplicate-send prevention, mailbox pool + warm-up + throttling + deliverability pause thresholds, DNS/domain checks, and CSV import / list verification. Deliverability lives here (no separate doc).
**Source sections:** Master guide §14 (sending/compliance/deliverability), §15 (CSV imports/list verification).
**Status:** Draft (MVP compliance baseline = United States -> [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md))
**Related docs:** [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`send_intents`, `outbound_messages`, `suppression_entries`, `tenant_compliance_profiles`) · [AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md) (groundedness, injection) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) (subscription gate) · [API_CONTRACT](API_CONTRACT.md) (`/send-gate/dry-run`)

---

## 1. Send gate purpose

The send gate is the **final server-side decision** before any outbound message is scheduled or sent. **No frontend button, agent node, n8n workflow, human reviewer, or provider callback can bypass it** (CLAUDE rule 9). It answers: *can this exact message be sent to this exact recipient from this exact mailbox at this exact time?*

## 2. Send gate checks

Subscription + usage quota · campaign status + approval mode · prospect/contact tenant ownership · suppression + unsubscribe state · contact validity + verification · message review status · **first-client manual approval policy** · **human edits re-grounded after latest edit** · prompt-injection + groundedness verdicts · compliance profile completeness · required footer/address/unsubscribe content · mailbox state/warm-up/domain auth/deliverability · per-mailbox/tenant/provider/campaign throttles · recipient local send window · idempotency + duplicate-send uniqueness · provider readiness/outage/pause.

## 3. No-send reason codes

| Code | Meaning | Result |
|---|---|---|
| `SUBSCRIPTION_INACTIVE` | Subscription blocks paid/write/send | Deny |
| `USAGE_LIMIT_EXCEEDED` | Quota reached | Deny |
| `CAMPAIGN_NOT_ACTIVE` | Campaign draft/paused/archived/completed | Deny |
| `CONTACT_SUPPRESSED` | Recipient suppressed | Deny |
| `CONTACT_UNSUBSCRIBED` | Recipient opted out | Deny |
| `CONTACT_INVALID_EMAIL` | Email missing/invalid | Deny |
| `CONTACT_VERIFICATION_FAILED` | Verification failed or prior bounce | Deny |
| `REVIEW_NOT_APPROVED` | Approval required but missing | Deny |
| `EDIT_REQUIRES_REGROUNDING` | Human edit not re-grounded | Deny |
| `GROUNDEDNESS_FAILED` | Unsupported claims remain | Deny |
| `PROMPT_INJECTION_FLAGGED` | Injection defense triggered | Deny |
| `COMPLIANCE_PROFILE_INCOMPLETE` | Sender/footer/unsubscribe/profile incomplete | Deny |
| `UNSUBSCRIBE_LINK_MISSING` | Unsubscribe mechanism missing | Deny |
| `FOOTER_MISSING` | Footer/disclosure missing | Deny |
| `MAILBOX_NOT_READY` | Mailbox not warm/paused/disabled/unhealthy | Defer |
| `DOMAIN_AUTH_FAILED` | SPF/DKIM/DMARC/PTR failed in production | Defer |
| `SEND_WINDOW_CLOSED` | Recipient local window closed | Defer |
| `THROTTLE_LIMIT_REACHED` | Mailbox/provider/campaign cap reached | Defer |
| `DUPLICATE_SEND_INTENT` | Unique intent already exists | Deny |
| `PROVIDER_PAUSED` | Provider paused/outage | Defer |

> `POST /send-gate/dry-run` returns this same decision engine result and **never sends**.

## 4. Compliance profile

`tenant_compliance_profiles` required before live sending; in mock mode, seed it but still read from it. Min fields: `tenant_id`, `sender_business_name`, `physical_mailing_address`, `default_unsubscribe_text`, `default_footer_text`, `cold_email_enabled`, `sms_enabled`, `legal_review_status` (`not_reviewed`/`approved`/`rejected`/`needs_changes`).

**Production live sending requires a complete compliance profile + legal/provider approval. SMS is post-MVP.** MVP compliance baseline = **United States** and first target market = **US** -> [ADR_COMPLIANCE_JURISDICTION](ADRs/ADR_COMPLIANCE_JURISDICTION.md).

## 4A. First real client sending policy

For the first real client, every AI-generated cold-email draft requires manual human approval, even after prompt-injection, groundedness, compliance, billing, and send gates pass.

Auto-send can be added later only as a per-tenant/per-campaign configuration. Auto-send must still require every safety gate to pass.

## 4B. P3-5a provider lane stop gate

P3-5a is an inspection/design checkpoint only. Future provider work must preserve this document's send-gate authority and add a provider interface behind a fail-closed adapter registry. A real adapter may only be reachable after owner decisions for provider choice, sending domain, DNS/SPF/DKIM/DMARC ownership, mailbox warm-up policy, tenant/provider caps, unsubscribe/legal copy, pilot domain, deliverability owner, and approved secret/config path.

Provider credentials must use secret references only. No raw provider secrets may be stored in DB rows, logs, audit events, frontend state, prompts, exports, or client responses.

P3-5b adds the provider interface boundary and fail-closed adapter registry. Only the network-free mock adapter is registered. `EMAIL_PROVIDER=mock` and `LIVE_EMAIL_SENDING_ENABLED=false` are the safe defaults; live provider names fail closed until a later owner-approved slice adds a real adapter and required secret/config checks.

P3-5c defines provider-selection and secret/config design. Provider choice is not final. The recommended default for a first internal-only technical smoke is Amazon SES if the deployment target remains AWS; Postmark is the alternate when owner prioritizes fastest dashboard/operator workflow. Final selection still requires owner approval for provider, sending domain, DNS owner, webhook scope, caps, legal copy, deliverability monitor, and internal-only smoke scope.

## 4C. Owner-approved sending decisions (P3-5d packet → P3-5e)

The owner answered the P3-5d packet on 2026-06-28 (recorded in [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS §2](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) and [evidence/phase-3-5e-owner-approval-resend-roadmap.md](evidence/phase-3-5e-owner-approval-resend-roadmap.md)). **This selects the pilot lane; it does NOT enable live sending** — `EMAIL_PROVIDER=mock`, `LIVE_EMAIL_SENDING_ENABLED=false`, and no Resend adapter is built. These decisions bind future provider work:

- **Provider:** **Resend** (main email provider).
- **Sending subdomain:** `outreach.automatedstructure.com` (dedicated cold-outreach subdomain per §7) unless owner later changes it.
- **Sender identity:** `From: AutomatedStructure <outreach@outreach.automatedstructure.com>`; `Reply-To: replies@automatedstructure.com` or another monitored owner-provided inbox.
- **Required unsubscribe footer (all outbound):** *"You are receiving this because we found your business contact for relevant B2B outreach. To stop receiving emails, unsubscribe here: {{unsubscribe_url}}."* Company/legal mailing details appended once final business address is confirmed; counsel sign-off on copy still pending.
- **First-pilot caps (conservative; override the §7 defaults downward for the first pilot):** tenant hourly **10**, tenant daily **50**, campaign daily **50**, mailbox/sender daily **25**. The §7 warm-up ramp and pause thresholds still apply; the lower of (§4C cap, §7 cap) wins.
- **Webhook event scope:** normalize `delivered`, `bounced`, `complained`, `deferred`, `failed`, and `unsubscribed/suppressed` (if supported by the normalized Resend event shape). **No open/click tracking** unless explicitly enabled later. Webhook **signature verification + idempotency required**; no raw payload leakage (rule 12/14).
- **First smoke is internal-only:** allowed only after DNS verification, Resend API + webhook secret_refs, legal footer, and all send gates pass. No prospect/client recipient during first smoke; external-recipient sending needs separate approval + green internal-smoke evidence.
- **Emergency stop:** owner/operator and engineering can emergency-stop; `LIVE_EMAIL_SENDING_ENABLED=false` (config/feature flag) disables live sending immediately.
- **Ownership:** owner/operator owns the Resend account and deliverability monitoring (bounces/complaints/DNS health/blocks/suppressions/warm-up) until a dedicated ops owner exists.

## 5. Suppression model

Append-only `suppression_entries` (tenant, contact/email/phone, channel, reason, source, actor, timestamp). Rules:

- `all` suppresses every channel. Email unsubscribe blocks email sends.
- Spam complaints suppress **all** future cold outreach to that email. Hard bounces suppress future email sends.
- Manual suppression requires actor + reason + audit.
- **Reinstatement requires an explicit permissioned event, not silent deletion.**

## 6. Duplicate-send prevention

- One deterministic send-intent key per prospect/campaign/draft version; `send_intents` unique active key; `outbound_messages.send_intent_id` unique.
- Send worker **locks row before provider call**; uses provider idempotency key when supported.
- Unknown provider result → provider lookup **before** retrying.

## 7. Mailbox pool & deliverability

Dedicated cold-outreach mailboxes/subdomains only; transactional providers reserved for account/billing/opted-in product email.

**Mailbox states:** `created`, `dns_pending`, `warming`, `warm`, `paused`, `degraded`, `blocked`, `retired`.

**Warm-up & throttles (defaults):**
- 10-day warm-up; start 5–10 sends/day; ramp gradually; silent 30+ days → back to warming.
- Inbox cap: 30 cold sends/day (hard max 50 unless owner approves). Provider cap: 20/hour/tenant/provider.
- Randomized interval 180–900 s. Recipient local window 8 AM–6 PM. Campaign- and tenant-level caps also apply.

**Pause thresholds:** bounce warn ≥1.0%, pause ≥2.0% · spam-complaint warn ≥0.05%, pause ≥0.1% · domain-auth failure pauses affected mailbox/domain · provider error spike pauses affected route.

**DNS/domain:** track SPF, DKIM, DMARC, PTR (where applicable), tracking-domain status, last verification timestamp. Mock adapter must produce realistic pass/fail states.

## 8. CSV imports & list verification

**Upload limits:** CSV only; MIME allowlist `text/csv`/`application/csv`/`text/plain` with CSV sniffing; max 10 MB; max 10,000 rows (plan-configurable); UTF-8 required (reject/normalize BOM); store original in object storage with SHA-256; production scan hook required before parsing.

**Validation:** header mapping · email format · at least email or phone (cold email requires email) · duplicate detection by tenant+email · suppression check · timezone validation (MVP may use tenant default) · prompt-injection/dangerous-content scan · max cell length · **formula-injection prevention** for values starting `=`/`+`/`-`/`@` unless escaped · whitespace/casing normalization · row-level error report.

**Import flow:** upload → backend scans/parses preview/validates headers → frontend mapping UI → backend returns accepted/duplicate/invalid-email/missing-timezone/suppressed/dangerous-content counts → user confirms → import worker processes rows + writes audit/import results.

**List verification before sends:** verify email via mock/live verifier; block invalid/disposable/bounced/suppressed; store result + timestamp; re-verify stale by policy; **campaign cannot schedule if required verification is missing.**

## 9. Send gate tests / acceptance

- [ ] Every no-send reason code reachable and exercised (worker + dry-run).
- [ ] No path can send bypassing the gate (UI/agent/n8n/reviewer/callback).
- [ ] Human edit forces re-grounding before send.
- [ ] Suppression honored after re-import; reinstatement only via permissioned event.
- [ ] Duplicate send attempt returns existing intent/message.
- [ ] Bounce/complaint thresholds pause mailboxes; domain-auth failure defers in production.
