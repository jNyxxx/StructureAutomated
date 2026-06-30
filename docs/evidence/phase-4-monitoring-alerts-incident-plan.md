# P4-Monitoring-Alerts-Plan — Monitoring, Alerts, Incident Ownership, and Rollback Plan

**Purpose:** Define monitoring, alerting, incident ownership, and rollback requirements for staging and first-pilot readiness.
**Slice:** P4-Monitoring-Alerts-Plan
**Date:** 2026-07-01
**Status:** Complete — docs-only plan. No code, package, config, secret, deployment, provider, billing, or production change.
**Base commit:** `afd7547 docs(p4): add first pilot readiness checklist`

---

## 1. Monitoring scope

This plan covers staging-first observability and first-pilot readiness only.

Scope rules:

- Staging must be monitored before first-pilot acceptance.
- First pilot monitoring must prove system safety, not public launch readiness.
- Production monitoring is a later Phase 5/cutover concern.
- This plan does not enable live providers, live cold outreach, Stripe money movement, SMS, live scraping, or production mode.
- Monitoring evidence must cover backend, frontend, database, Redis/rate limit, auth, billing/access gates, send gates, audit logging, jobs/workers, config/boot guard, and security/compliance signals.

---

## 2. Required alert categories

| Alert category | Condition to watch | Blocks staging acceptance? | Notes |
|---|---|---:|---|
| Backend health/readiness failure | `/health`, `/live`, or `/ready` fails or returns degraded dependency state. | Yes | Readiness must include DB, migration, and rate-limit backend status where configured. |
| Frontend availability failure | Staging frontend does not load, login page unavailable, or dashboard route fails. | Yes | Must test both unauthenticated and authenticated flow. |
| Database connectivity failure | Backend cannot connect to DB or DB errors spike. | Yes | Must not accept staging with DB flapping. |
| Migration mismatch | Runtime code and migration head are out of sync. | Yes | Requires migration approver review before proceeding. |
| Redis/rate-limit backend failure | Redis unavailable when configured, or rate-limit readiness fails. | Yes | Rate limiting should fail closed and report safe readiness status. |
| Auth/JWKS failure | Clerk/JWKS token verification fails unexpectedly, issuer/audience/AZP mismatch, or auth smoke fails. | Yes | If limited mock-staging auth is used, it must be explicitly approved and labeled. |
| Billing/access-gate errors | `is_active`, `has_feature`, or derived access gates behave unexpectedly. | Yes | Must protect costly/outbound features. |
| Send-gate errors | Send gate produces unexpected allow/block result or missing reason code. | Yes | No outbound path can bypass review, billing, suppression, or compliance. |
| Webhook verification failures | Signed webhook verification fails repeatedly or unsigned requests are accepted. | Yes for provider smoke | Test-mode/internal smoke only; no live provider path without approval. |
| Unexpected live-provider flag active | Any live-provider or payment flag is active without explicit approval. | Yes | Immediate hard stop. |
| Error-rate spike | Application errors exceed agreed threshold during smoke or pilot. | Yes if sustained or unexplained | Threshold must be locked by owner/ops before staging. |
| 5xx spike | HTTP 5xx rate exceeds threshold during smoke or pilot. | Yes if sustained or unexplained | Default proposal: investigate any repeated 5xx during smoke. |
| Worker/job failure | Worker task fails, retries loop, or job age grows. | Yes if required for smoke | Worker may remain intentionally disabled if owner-approved for limited staging. |
| Queue/DLQ growth | Queue age/depth grows or DLQ receives jobs. | Yes if queue is in scope | Replay requires idempotency review. |
| Audit logging failure | Risky action occurs without audit record. | Yes | Includes auth/admin/billing/review/send-gate/provider-smoke actions. |
| Suspicious tenant isolation/RLS error | Cross-tenant access, missing tenant context, or RLS/object-auth anomaly. | Yes | Treat as SEV-1 until proven safe. |
| Secret/config boot-guard failure | Boot guard rejects unsafe config or detects placeholder/unsafe secret path. | Yes | Do not bypass boot guard. |

---

## 3. Required owners

These owner values must be named before staging acceptance or pilot entry.

| Owner role | Required before | Responsibility |
|---|---|---|
| Alert recipient | P4-5/P4-6/P4-9 | Receives automated/manual staging smoke and incident alerts. |
| Incident owner | P4-5/P4-9 | Owns triage, incident notes, severity, and closeout. |
| Deployment approver | P4-4/P4-5 | Approves staging release action. |
| Migration approver | P4-5/P4-6 | Approves schema migration and confirms migration evidence. |
| Rollback approver | P4-5/P4-6 | Approves image/config rollback or forward-fix decision. |
| Emergency-stop owner | P4-7/P4-8/P4-9 | Can stop provider/billing/sending smoke paths quickly. |
| Billing owner | P4-7/P4-10 | Owns billing/access state decisions and Stripe test/live boundaries. |
| Deliverability owner | P4-8/P4-10 | Owns email/domain/suppression and deliverability risk decisions. |
| Security/compliance owner | P4-3/P4-5/P4-10 | Owns auth, tenant isolation, compliance, data handling, and risk acceptance. |

Current status: these values are not locked in the owner-response tracker, so staging and pilot remain blocked.

---

## 4. Severity levels

| Severity | Examples | Response target | Escalation path |
|---|---|---|---|
| SEV-1 | Tenant isolation/RLS failure; live provider or payment mode unexpectedly active; boot guard bypass; secrets exposed; duplicate live send risk. | Immediate response; stop affected path first. | Alert recipient → incident owner → security/compliance owner → William. |
| SEV-2 | Backend readiness failure; DB unavailable; migration mismatch; auth/JWKS failure; sustained 5xx spike; audit logging failure. | Triage within 30 minutes during staging/pilot window. | Alert recipient → incident owner → deployment/rollback approver. |
| SEV-3 | Non-critical frontend route failure; worker/job retry issue; degraded monitoring; billing/send-gate mismatch with no live impact. | Triage same day during staging/pilot window. | Alert recipient → feature owner → incident owner if repeated. |
| SEV-4 | Documentation gap, low-risk dashboard warning, non-blocking test-data issue, minor alert noise. | Triage before pilot go/no-go. | Feature owner → docs/evidence owner. |

Severity can be raised by the incident owner if customer data, billing, provider, auth, tenant isolation, or compliance risk is involved.

---

## 5. Staging smoke observability

### Logs to inspect

- Backend structured logs for request ID, tenant ID, actor ID, route, status, and safe error code.
- Frontend runtime/build logs for route failures and auth/session errors.
- Worker logs for job lifecycle, retry, idempotency, and DLQ behavior if worker is enabled.
- Migration logs for current revision and migration result.
- Auth logs for JWKS/issuer/audience/AZP/MFA verification status without exposing tokens.
- Billing/send-gate logs for safe gate reason codes.
- Webhook logs for signature verification result and idempotency decision when smoke is approved.
- Boot guard/readiness logs for config safety results.

Logs must not expose secrets, tokens, raw provider payload secrets, raw credentials, or sensitive client data.

### Health endpoints to check

- Backend `/health`.
- Backend `/live`.
- Backend `/ready`.
- Frontend login page.
- Frontend authenticated dashboard route.
- Any staging smoke-specific synthetic route or scripted browser check once implemented.

### Audit records to confirm

- Login/auth/session action.
- Tenant/user/admin action.
- Campaign creation or update.
- Draft review decision.
- Send-gate dry run and result.
- Mock/send-intent or provider-smoke action if approved.
- Billing/access gate action.
- Suppression/compliance action.
- Webhook event receipt if test/internal smoke is approved.

### Failures that block staging acceptance

- Any failed readiness dependency without owner-approved exception.
- Migration mismatch.
- Auth path not verified.
- Missing audit record for risky action.
- Tenant isolation/RLS/object-auth anomaly.
- Billing or send gate unexpected allow result.
- Secret/config boot-guard failure.
- Live-provider/payment flag active without approval.
- Alert recipient, incident owner, migration approver, or rollback approver missing.

---

## 6. Rollback plan

| Rollback area | Procedure | Required owner |
|---|---|---|
| Package rollback | Restore package files from previous known-good commit, run deterministic install, then rerun frontend gates. | Rollback approver + feature owner. |
| Frontend image rollback | Revert to previous approved image tag/task definition after frontend smoke failure. | Rollback approver + deployment approver. |
| Backend image rollback | Revert to previous approved image tag/task definition after backend smoke failure. | Rollback approver + deployment approver. |
| Migration rollback / forward-fix | Prefer forward-fix for non-destructive issues; do not blindly roll back DB after destructive migration. Snapshot/restore requires migration and rollback approver. | Migration approver + rollback approver. |
| Config rollback | Restore previous approved config refs/values through approved config system; do not commit secrets. | Config owner + rollback approver. |
| Provider flag rollback | Return provider/billing/sending flags to disabled or smoke-safe values; confirm readiness and logs. | Emergency-stop owner + billing/deliverability owner. |
| Emergency stop | Disable affected provider/sending/billing path, pause workers if needed, record incident, notify William, and preserve evidence. | Emergency-stop owner + incident owner. |

Rollback evidence must include timestamp, owner, reason, affected service, previous and restored version/config reference, verification steps, and final status.

---

## 7. Hard stops

Stop immediately if any condition is true:

- no alert recipients;
- no rollback owner;
- no migration approver;
- no incident owner;
- boot guard is weakened or bypassed;
- logs expose secrets or sensitive client data;
- live provider flags are active unexpectedly;
- staging smoke is accepted without evidence;
- production is selected accidentally;
- auth, RBAC, RLS, tenant isolation, billing gates, send gates, suppression, or audit are weakened;
- migration mismatch is ignored;
- provider or billing smoke proceeds without named emergency-stop owner.

---

## 8. William-facing questions

William must answer these before staging acceptance or pilot entry:

1. Who receives staging and pilot alerts?
2. Who owns incidents and writes the incident record?
3. Who approves rollback decisions?
4. Who approves database migrations?
5. What monitoring/logging system should be used for staging?
6. What log retention period is expected for staging and pilot evidence?
7. Who is the emergency-stop owner for provider/billing/sending smoke?
8. What is the escalation channel: Slack, email, phone, or another system?
9. What response-time expectations apply during the first pilot window?
10. Who can formally accept monitoring or dependency risk if a non-critical issue remains?

---

## 9. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS. |
| `git status --short` | PASS — only intended docs changed before commit. |
| Package/source/config scope | PASS — no package, backend, frontend source, config, `.env`, Dockerfile, workflow, or deployment file changes. |
| Unsafe-claim grep | PASS — only pre-existing Phase 4 exit-criteria wording was found; no new active-state claim was added. |
| Secret-pattern check | PASS. |
| Registry/deployment activity | PASS — none performed. |
| Safety boundary | PASS — docs-only monitoring/alerts/incident/rollback plan. |

---

## 10. Final verdict

- P4-Monitoring-Alerts-Plan complete.
- Boss demo remains allowed.
- Staging remains blocked.
- Production remains blocked.
- Monitoring/alert owners are still waiting for William/operator values.
