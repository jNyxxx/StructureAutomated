# n8n Workflow Plan

**Purpose:** Docs-only plan for n8n's role, boundaries, and future workflow catalog in AutomatedStructure.
**Source sections:** [ARCHITECTURE](../ARCHITECTURE.md) (component ownership) · [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) §7 (n8n boundaries — canonical) · [API_CONTRACT](../API_CONTRACT.md) §7 (webhook verification) · [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md) §1 (send gate).
**Status:** Draft — open owner decisions pending in §12.
**Related docs:** [ARCHITECTURE](../ARCHITECTURE.md) · [API_CONTRACT](../API_CONTRACT.md) · [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) · [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md) · [AI_SAFETY_AND_GROUNDEDNESS](../AI_SAFETY_AND_GROUNDEDNESS.md) · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md) · [PHASE_4_IMPLEMENTATION_PLAN](../PHASE_4_IMPLEMENTATION_PLAN.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md)

---

## 1. Executive summary

n8n is optional automation/notification orchestration glue — it is not, and must never become, core system logic. In plain terms: n8n is allowed to *tell people things happened* (send a Slack message, forward a safe webhook, remind someone of a task). It is never allowed to *decide* whether something is allowed to happen (send an email, charge a card, approve a draft, grant access).

Zero workflows currently exist in n8n, and that is the correct state for local/mock MVP. Nothing in the local demo, the E2E smoke script, or the stability smoke script depends on n8n having any workflows configured. This doc exists so that when workflows eventually get built — after William approves staging or a first real client — they get built inside firm boundaries instead of by ad hoc invention.

## 2. Current status

- The `n8n` service runs in `docker-compose.yml` as part of the core local stack (`n8nio/n8n:1.70.0`, port `5678`, basic auth via `N8N_USER`/`N8N_PASSWORD`).
- Its only persistent volume is `n8n_data:/home/node/.n8n` — n8n's own internal data directory. There is no workflow-file bind mount from the repo, so nothing about n8n's contents is version-controlled, and (confirmed) no workflows currently exist inside it.
- No workflows are required to pass the local demo, `local_e2e_smoke.py`, or `local_stability_smoke.py`. All three exercise the backend/frontend/worker path directly and never call n8n.
- The local demo works identically whether n8n has zero workflows or is not running at all.
- Building real workflows requires William's approval, tied to the staging or first-client phase (see §4, §12).

## 3. n8n boundaries

**n8n may:**
- Send notifications, alerts, and summaries (Slack/Teams/email).
- Forward safe, already-verified webhook payloads.
- Send task reminders and human-review notifications.
- Trigger scheduled campaign runs, inject mock outcomes for demo purposes, and receive provider-like mock callbacks (existing local/demo-oriented allowances from [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) §7).
- Trigger a daily deliverability monitor check (read-only trigger; the backend does the actual check).
- Surface internal operational alerts.

**n8n must never:**
- Enforce or bypass auth, RBAC, RLS, or tenant isolation.
- Make billing or access decisions, or mark billing state active.
- Make compliance or suppression decisions.
- Make send-gate decisions or override a no-send reason code.
- Make groundedness or AI-safety decisions.
- Bypass human approval.
- Hold real sending authority — it never sends a cold outreach or transactional message itself.
- Handle production secrets directly outside the approved secret system (secret references only, resolved by the backend).
- Enable a provider (billing, sending, SMS, scraping) without explicit owner approval.
- Access the database directly, or store tenant secrets outside approved storage.

These must-never items are a strict superset of the existing hard rule in [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) §7 ("n8n must not bypass backend auth, send messages directly, mark billing active, disable gates, access the DB directly, or store tenant secrets outside approved storage") and the send-gate rule in [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md) §1 ("No frontend button, agent node, n8n workflow, human reviewer, or provider callback can bypass it").

## 4. Recommended workflow phases

**Phase A — Local/mock MVP (current phase)**
Status: no required n8n workflows. Optional docs-only placeholders, none required to ship or demo:
- Demo activity summary
- Internal smoke result notification
- Manual review notification mock

**Phase B — First-client/staging prep (requires William approval to start)**
Recommended safe workflows:
- Draft Needs Review notification
- Send-gate blocked notification
- Failed job/error alert
- Daily activity summary
- First-client onboarding checklist reminder
- Compliance/suppression change alert

**Phase C — Production-approved future (requires William approval per workflow, after Phase B is live)**
Potential workflows only after approval:
- Slack/Teams review alerts (superset of Phase B's single-channel alert)
- Incident escalation
- Provider webhook forwarding
- Onboarding task automation
- Daily/weekly client reports
- CRM handoff notifications

## 5. Specific proposed workflows

### A. Draft Needs Review Alert
- **Trigger:** backend records a review item pending (draft reaches `needs_review`/`pending_review` state).
- **Backend event/API source:** review-queue write in the drafts/review service; proposed event `draft.review_pending`.
- **n8n action:** notify Slack/Teams/email internal reviewer with a link to the review queue.
- **Safety rules:** n8n must not approve drafts; n8n must not send cold emails; notification is read-only/informational.
- **Required secrets/config later:** Slack/Teams webhook URL or email relay credential (secret ref only).
- **Local/mock behavior:** no-op / not wired; local demo reviewers use the app UI directly.
- **Production approval required:** yes (Phase B).
- **Failure behavior:** notification failure does not block the review item from existing or being approved through the UI.

### B. Send Gate Blocked Alert
- **Trigger:** send-gate dry run or a real send intent returns a no-send reason code.
- **Backend event/API source:** send-gate evaluation result; proposed event `send_gate.blocked` carrying the reason code.
- **n8n action:** notify internal operator with the reason code(s) and tenant/campaign context (redacted).
- **Safety rules:** n8n must not override, retry around, or reinterpret the gate result; it only reports it.
- **Required secrets/config later:** same notification channel as Workflow A.
- **Local/mock behavior:** no-op; blocked sends are already visible via `/send-gate/dry-run` and app UI.
- **Production approval required:** yes (Phase B).
- **Failure behavior:** notification failure never changes the gate outcome; the gate remains fail-closed regardless of n8n availability.

### C. Failed Job / Error Alert
- **Trigger:** backend worker/job failure, dead-letter event, or repeated 5xx pattern.
- **Backend event/API source:** worker dead-letter/audit event; proposed event `job.dead_lettered` or `ops.error_spike`.
- **n8n action:** notify internal ops channel with job id, correlation id, and error class (no payload/PII).
- **Safety rules:** n8n must not retry unsafe send actions directly, and must not re-trigger the failed job itself — retries stay backend-owned.
- **Required secrets/config later:** ops channel webhook.
- **Local/mock behavior:** no-op; local smoke scripts already assert on job outcomes directly.
- **Production approval required:** yes (Phase B).
- **Failure behavior:** fails open — a missed alert does not stop backend dead-letter/retry handling.

### D. Daily Local/Client Activity Summary
- **Trigger:** scheduled daily (n8n cron trigger).
- **Backend event/API source:** read-only reporting endpoint(s) summarizing campaigns, drafts, approvals, sends, bounces/mock sends, and audit highlights for the day.
- **n8n action:** compile and send a daily summary to Slack/Teams/email.
- **Safety rules:** read-only; backend remains the source of truth; no PII beyond what's already approved for internal ops visibility.
- **Required secrets/config later:** reporting endpoint API key (secret ref), notification channel.
- **Local/mock behavior:** optional Phase A placeholder only, disabled by default.
- **Production approval required:** yes for external/client-facing use; optional/internal-only version could ship in Phase B.
- **Failure behavior:** fails open; a missed summary has no functional effect on the system.

### E. First-Client Onboarding Checklist Reminder
- **Trigger:** scheduled or manual.
- **Backend event/API source:** none required — this is a static/templated reminder, optionally reading onboarding checklist status from the backend.
- **n8n action:** remind the owner about domain/DNS, compliance jurisdiction, mailbox pool, billing decision, reviewer assignment, and suppression policy.
- **Safety rules:** no provider setup is performed automatically; this workflow only reminds, never configures.
- **Required secrets/config later:** notification channel only.
- **Local/mock behavior:** not applicable locally (no real client to onboard).
- **Production approval required:** yes (Phase B, ties to first real client).
- **Failure behavior:** fails open.

### F. Compliance/Suppression Change Alert
- **Trigger:** suppression list, unsubscribe, or compliance profile update.
- **Backend event/API source:** suppression/compliance-profile write path; proposed event `compliance.suppression_changed`.
- **n8n action:** notify internal owner of the change (actor, reason, timestamp — no raw contact PII beyond what's already approved for suppression records).
- **Safety rules:** n8n must not edit suppression data itself unless explicitly approved in a future slice; this workflow is notify-only.
- **Required secrets/config later:** notification channel.
- **Local/mock behavior:** no-op.
- **Production approval required:** yes (Phase B).
- **Failure behavior:** fails open; suppression writes are unaffected by notification delivery.

### G. Incident Escalation Workflow
- **Trigger:** health/ready check failure, or smoke/stability script failure in staging/production.
- **Backend event/API source:** health/readiness endpoint failure or CI/ops alert; proposed event `ops.incident_detected`.
- **n8n action:** alert the owner/on-call channel.
- **Safety rules:** n8n must not deploy, roll back, or otherwise remediate automatically — it only alerts.
- **Required secrets/config later:** incident channel webhook/paging integration.
- **Local/mock behavior:** no-op; local smoke failures already surface directly in script output.
- **Production approval required:** yes (Phase C).
- **Failure behavior:** fails open; incident detection/response stays a human/ops-runbook process regardless of n8n availability.

## 6. Event/API contract assumptions

These are **proposed**, not implemented, unless a doc/section is cited as existing. Real workflows must confirm each item against the live API/worker code before relying on it.

- **Standard job/event envelope** (existing, from [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) §3 and [AUTH_AND_RBAC](../AUTH_AND_RBAC.md) §6): `tenant_id`, `actor_user_id`/`system_actor`, `correlation_id`, `job_id`, `idempotency_key`, `requested_permission`. Any event n8n consumes should carry these fields.
- **Inbound n8n webhook route** (existing, [API_CONTRACT](../API_CONTRACT.md) §7): `POST /webhooks/n8n/{name}`, verified via HMAC or shared-secret header, rotatable, fail-closed. Event names under `{name}` for the workflows in §5 (e.g. `draft-review-pending`, `send-gate-blocked`) are **proposed**, not yet implemented.
- **Generic webhook flow** (existing, [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md) §8): verify raw-body signature before parsing → store first in `webhook_events` → return 2xx only after durable storage → dedupe by provider event id → process asynchronously via queue → idempotent → audit. Any n8n-facing outbound trigger from the backend should follow the same shape in reverse (durable outbox entry before dispatch attempt).
- **Idempotency** (existing, [API_CONTRACT](../API_CONTRACT.md)): API actions use `Idempotency-Key`; webhooks dedupe by provider event id. n8n-triggered notifications should carry a deterministic key (e.g. `job_id` + event type) so retried deliveries don't double-notify.
- **No-send reason codes** (existing, [EMAIL_COMPLIANCE_AND_SEND_GATE](../EMAIL_COMPLIANCE_AND_SEND_GATE.md)): the full code table (`SUBSCRIPTION_INACTIVE`, `CONTACT_SUPPRESSED`, `GROUNDEDNESS_FAILED`, etc.) is a read-only input n8n may display in Workflow B — never generate or override.
- **Correlation/audit ids**: `correlation_id`, `job_id`, and `audit_id`/`send_intent_id` (per relevant flow) should be included in any notification payload for traceability back to the backend audit trail.
- **Redaction rule**: notification payloads must never include secrets, raw provider credentials, full contact PII, or raw AI prompt/context content — summarized/redacted fields only.
- **Retry/dead-letter**: n8n-triggered notification deliveries should have bounded retries (matching the general job retry posture in [WORKERS_QUEUE_AND_WEBHOOKS](../WORKERS_QUEUE_AND_WEBHOOKS.md)) and fail open rather than blocking the originating backend flow.

## 7. Security and secrets plan

- No secrets are ever stored in workflow JSON.
- Real credentials come from the approved secret manager (AWS Secrets Manager per [CLAUDE.md](../../CLAUDE.md) §10) once workflows go live — never hardcoded in n8n.
- Local/demo placeholders only until then; current `.env.example` n8n basic-auth values (`N8N_USER`/`N8N_PASSWORD`) are local-dev-only, not real secrets.
- Webhook signatures (HMAC/shared-secret, fail-closed) are required for any inbound `/webhooks/n8n/{name}` route before it's relied upon.
- n8n's own credentials/API keys use least-privilege scopes — read/notify-only where possible, never a privileged or platform-admin-equivalent principal.
- Payloads sent to or from n8n must be tenant-safe and redacted per §6.
- No raw prospect PII appears in notifications unless explicitly approved per workflow.
- No AI prompt/context content, groundedness verdict detail, or agent reasoning is leaked into notification payloads.
- Logs of n8n-related activity follow the same redaction rules as all other backend logs — no secrets, ever.

## 8. Failure behavior

- n8n failure or downtime must not block any core backend flow unless a future slice explicitly designs it that way (none currently do).
- Notifications fail open: a missed Slack/Teams/email message is an inconvenience, not a safety incident.
- Send-gate, compliance/suppression, billing, and security gates fail closed in the backend regardless of n8n's state.
- Workflow retries must be bounded — no unbounded retry loops.
- Duplicate notifications should be prevented via idempotent delivery keys (§6).
- An n8n outage must never allow an unauthorized send, billing change, or approval — all of those remain backend-enforced independent of n8n.

## 9. Local workflow stance

- Do not create workflows now.
- Keep n8n empty for MVP unless William explicitly asks for a demo workflow.
- If a demo ever wants n8n involved, build a mock notification workflow only — never a workflow with real sending, billing, or data-mutation authority.
- Local smoke (`local_e2e_smoke.py`) and stability smoke (`local_stability_smoke.py`) must remain fully independent of n8n; no future n8n workflow may become a required dependency of either script.

## 10. First workflow to build later

**Recommendation: Draft Needs Review Alert (Workflow A, §5).**

Reason:
- Safe — pure notification, no data mutation.
- Useful — closes a real gap (reviewers currently must poll the UI).
- Low risk — failure mode is "nobody got pinged," not a security or compliance incident.
- Does not alter data — read-only trigger off an existing state transition.
- Does not send emails — it notifies a human about a draft; it never sends the draft itself.
- Supports human approval — it strengthens the human-in-the-loop review step rather than working around it.

## 11. Acceptance checklist

A workflow may be built only when all of the following are true:

- [ ] Owner (William) has approved this specific workflow.
- [ ] No safety/security/compliance gate can be bypassed by the workflow.
- [ ] The workflow has no real sending authority.
- [ ] No secrets appear in the workflow JSON.
- [ ] Payloads are redacted per §7.
- [ ] Inbound webhooks are signed/verified per §6.
- [ ] Idempotency/duplicate-delivery has been considered.
- [ ] Failure mode is documented (fail open vs. fail closed, and why).
- [ ] Audit trail/traceability (correlation id, job id) has been considered.
- [ ] Local/test proof has been captured before enabling in any shared environment.

## 12. Open decisions for William

1. Slack or Teams (or email) for internal notifications?
2. Who receives Draft Needs Review / Send Gate Blocked alerts?
3. Should daily activity summaries be sent, and to whom?
4. What channel should incident escalation (Workflow G) use?
5. What client data, if any, may appear in notification payloads?
6. When should the first n8n workflow be enabled — staging, or only after the first real client?
7. Who owns/holds the n8n credentials (Slack/Teams webhook secrets, notification channel API keys)?
8. Confirm: should the first workflow built be Draft Needs Review Alert (§10)?
