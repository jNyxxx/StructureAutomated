# P4-Demo-Walkthrough — Boss Demo Walkthrough Script and QA Checklist

**Purpose:** Give William a clean, repeatable walkthrough for the local/mock AutomatedStructure MVP demo.
**Slice:** P4-Demo-Walkthrough
**Date:** 2026-06-30
**Status:** Complete — docs-only demo script. No code changes, deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping.
**Base commit:** `e4c9e61 docs(p4): add owner response tracker`
**Related docs:** [phase-3-final-boss-handoff-package](phase-3-final-boss-handoff-package.md) · [phase-3-demo-1-mock-send-path-readiness](phase-3-demo-1-mock-send-path-readiness.md) · [phase-3-demo-2-local-mock-auth-readiness](phase-3-demo-2-local-mock-auth-readiness.md) · [phase-4-1b-owner-response-tracker](phase-4-1b-owner-response-tracker.md)

---

## 1. Demo objective

Show William that the local/mock MVP works end-to-end without enabling any live provider or production environment.

Primary points to prove:

- The local/mock MVP can be reviewed in the browser.
- Login works through the local/mock demo account.
- Campaign, draft, review, send-gate, mock-send, outbound, audit, billing-gate, compliance, deliverability, and outcomes screens are demoable.
- Cold outreach is mock-only.
- Resend is transactional/opted-in only and remains disabled/fail-closed.
- Stripe is fail-closed; checkout and billing portal do not move money.
- No live providers are enabled.
- No deployment, AWS provisioning, registry push, production launch, SMS, or live scraping has occurred.

Suggested opening line:

> This is the completed local/mock MVP demo. It shows the product flow and the safety gates, but it does not send real email, charge money, touch AWS, or run in production.

---

## 2. Pre-demo setup

### 2.1 Repo and commit

```text
Repo path: D:\AutomatedStructure
Branch: master
Latest expected commit for this walkthrough: e4c9e61 docs(p4): add owner response tracker
```

Before starting, confirm:

```bash
git fetch origin
git status --short
git log --oneline -1
git ls-remote origin refs/heads/master
```

Expected result:

```text
git status --short is empty
HEAD matches origin/master
latest commit is e4c9e61 or newer walkthrough commit
```

### 2.2 Start local stack

From `D:\AutomatedStructure`:

```bash
docker compose up
```

Expected local services:

| Service | URL / port | Purpose |
|---|---|---|
| Frontend | `http://localhost:3000` | Browser demo UI |
| Backend | `http://localhost:8000` | Local/mock API |
| Demo login | `http://localhost:3000/login` | Local/mock sign-in page |
| Optional n8n | `http://localhost:5678` | Optional workflow UI |

### 2.3 Demo login

Use either method:

| Method | Expected result |
|---|---|
| Click `Continue with Demo Account` | Redirects to `/dashboard` as the seeded demo owner. |
| Email/password: `test@example.com` / `password` | Redirects to `/dashboard` as the seeded demo owner. |

The local/mock browser identity uses seeded demo values from P3-Demo-2. The visible user should be the demo owner/tenant, not a real Clerk user.

### 2.4 Health and readiness checks

Before showing the demo, confirm the local services respond:

```text
Frontend page loads: http://localhost:3000/login
Backend health:      http://localhost:8000/health
Backend live:        http://localhost:8000/live
Backend ready:       http://localhost:8000/ready
```

Expected result:

- login page loads;
- `/health` returns OK;
- `/live` returns OK;
- `/ready` is OK for the local/demo runtime or clearly reports a known local-only readiness limitation from the current stack.

Do not claim staging or production readiness from these checks. They are local/demo checks only.

---

## 3. Demo script

Use this script in order. Each step includes what to click/show, expected result, and the message to say to William.

### Step 1 — Login

| Action | Expected result | Say this |
|---|---|---|
| Open `http://localhost:3000/login`. Click `Continue with Demo Account` or use `test@example.com` / `password`. | Browser redirects to `/dashboard`. | The demo uses local/mock auth only. No real Clerk credentials are needed for this review. |

### Step 2 — Dashboard

| Action | Expected result | Say this |
|---|---|---|
| Show `/dashboard`. Point out overview metrics and local/mock safety labels. | Dashboard loads with mock KPIs and demo data. | This is the boss-review dashboard. It is useful for product review, not production metrics. |

### Step 3 — Contacts / prospects

| Action | Expected result | Say this |
|---|---|---|
| Open contacts/prospects/import area. Show contact list, mock enrichment/prospect data, and suppression visibility if available. | Contacts/prospects load from local/mock API. | This proves the CRM/prospect side is wired for demo data while keeping real research/scraping disabled. |

### Step 4 — Campaign flow

| Action | Expected result | Say this |
|---|---|---|
| Open campaigns. Create or select a campaign. Choose contacts/segment if available. | Campaign flow is visible and accepts local/mock data. | This is the core user workflow: build a campaign before any draft or send step can happen. |

### Step 5 — Draft generation

| Action | Expected result | Say this |
|---|---|---|
| Generate or open an AI/mock draft for the campaign. | Draft content appears in the UI. | Draft generation is mock/grounded for the demo. It shows how the agent output will be reviewed before sending. |

### Step 6 — Evidence / grounding view

| Action | Expected result | Say this |
|---|---|---|
| Open the evidence/grounding section for the draft. | Evidence/citations/grounding details are visible where the UI supports them. | The system is designed to show why the draft was generated and what evidence supports it. |

### Step 7 — Review queue

| Action | Expected result | Say this |
|---|---|---|
| Open the review queue. Select a draft awaiting review. | Draft appears with review actions. | Human review is mandatory before the send flow. Approval does not bypass safety gates. |

### Step 8 — Human approval

| Action | Expected result | Say this |
|---|---|---|
| Approve the draft from review queue. | Approved status/action is recorded. | This proves the human-in-the-loop step works. It still does not send anything live. |

### Step 9 — Send-gate dry run

| Action | Expected result | Say this |
|---|---|---|
| Run the send-gate dry run. | Gate result appears with pass/block reasons. | The send gate checks billing, review approval, suppression, compliance, and safety conditions. Dry run never sends. |

### Step 10 — Mock send intent

| Action | Expected result | Say this |
|---|---|---|
| Create/trigger send intent from the approved/gated item. | Mock outbound intent is created. | This is a production-shaped mock send. It records what would happen without contacting a live provider. |

### Step 11 — Outbound message record

| Action | Expected result | Say this |
|---|---|---|
| Open outbound messages/logs. | Outbound record appears with mock status such as `mock_sent` or blocked status if a gate fails. | The system records outbound attempts for auditability, even in mock mode. |

### Step 12 — Audit trail

| Action | Expected result | Say this |
|---|---|---|
| Open audit trail/logs. Show entries for login/campaign/review/send-gate/outbound actions where available. | Audit records are visible. | Every risky action must leave an audit trail. This is one of the production-safety foundations. |

### Step 13 — Billing / access gates

| Action | Expected result | Say this |
|---|---|---|
| Open billing/access page or show billing-gate result in send flow. | Mock billing/access state is visible; Stripe checkout/portal remains unavailable. | Billing gates exist, but real Stripe money movement is disabled and fail-closed. |

### Step 14 — Suppression / compliance

| Action | Expected result | Say this |
|---|---|---|
| Open suppression/compliance area. Show suppression list or compliance profile where available. | Compliance/suppression data is visible. | The send gate checks suppression and compliance before any outbound path. |

### Step 15 — Deliverability / outcomes dashboards

| Action | Expected result | Say this |
|---|---|---|
| Open deliverability and outcomes dashboards. | Mock deliverability/outcome metrics are visible. | These dashboards show the intended monitoring/read path; live provider data is not connected yet. |

### Step 16 — Sign out / sign in again

| Action | Expected result | Say this |
|---|---|---|
| Sign out, return to login, then sign in again with demo account. | Sign-out clears the demo session; sign-in returns to dashboard. | The local/mock browser session is usable and repeatable for boss review. |

---

## 4. Safety proof section

Use this language when William asks whether the demo is live.

### 4.1 No real email is sent

- The demo send path uses the mock sender.
- Send-gate dry run never sends.
- Mock send intent creates records only.
- Live email flags remain disabled.

Say:

> The demo proves the send workflow, but no real email leaves the system.

### 4.2 Cold outreach cannot route through Resend

- Cold outreach is intentionally separate from Resend.
- Resend is reserved for future transactional/opted-in sends only.
- The cold-outreach path is guarded and mocked.

Say:

> Cold outreach cannot use Resend. The architecture separates transactional email from cold outreach, and cold outreach remains mock-only.

### 4.3 Resend is disabled/fail-closed

- Resend real-send prerequisites are still missing.
- Provider flags remain disabled.
- Resend smoke requires later owner approvals and legal/DNS values.

Say:

> Resend is not active in this demo. It is blocked until provider refs, DNS, legal footer, internal recipient, deliverability owner, and emergency-stop owner are locked.

### 4.4 Stripe checkout/portal fail closed

- Stripe checkout and portal skeletons return unavailable/fail-closed behavior.
- No live Stripe keys are present.
- No subscription charge or customer sync is active.

Say:

> Stripe is intentionally fail-closed. Billing logic can be reviewed, but no checkout, portal, or money movement is enabled.

### 4.5 No production or infrastructure work happened

- No AWS account/region is locked.
- No staging domains are locked.
- No registry target is locked.
- No deployment has occurred.
- No production cutover has occurred.

Say:

> This is still local/mock. There is no AWS provisioning, no registry push, no staging deployment, and no production environment.

### 4.6 SMS and live scraping are disabled

- SMS provider work is deferred.
- Live scraping/paid research requires separate approval.
- No SMS/live scraping implementation is enabled.

Say:

> SMS and live scraping are not part of this live path. They remain deferred and blocked.

---

## 5. Demo troubleshooting

### Login page not loading

Check:

```text
Is Docker Desktop running?
Is frontend container running?
Is port 3000 already in use?
Open http://localhost:3000/login directly.
```

Fix:

```bash
docker compose down
docker compose up
```

If port conflict persists, stop the other process using port `3000` or update only local run settings after approval.

### Demo login not working

Check:

```text
The login route is http://localhost:3000/login.
The demo button should be visible in local/mock mode.
Credentials are test@example.com / password.
Browser localStorage may contain stale session data.
```

Fix:

```text
Sign out if possible.
Clear site data/localStorage for localhost:3000.
Reload the login page.
Restart frontend container if needed.
```

Do not add real Clerk credentials for the local/mock demo.

### Backend unavailable

Check:

```text
Backend container is running.
http://localhost:8000/health responds.
Backend logs do not show boot failure.
Port 8000 is not occupied by another service.
```

Fix:

```bash
docker compose down
docker compose up
```

If backend still fails, inspect logs for DB connection, migration, or configuration errors.

### Frontend cannot reach backend

Check:

```text
NEXT_PUBLIC_API_BASE_URL should point to http://localhost:8000 for local demo.
Backend health endpoint responds.
Browser console/network tab shows whether requests reach :8000.
```

Fix:

```text
Restart frontend after confirming local env/config.
Avoid editing real .env files for this demo unless explicitly approved.
```

### `/ready` not OK

Check:

```text
Database container is running.
Migrations are applied.
Redis readiness may depend on whether cache profile is enabled.
```

Fix:

```bash
docker compose down
docker compose up
```

If readiness reports migrations out of date, run the approved local migration command from the existing runbook only. Do not treat local readiness as staging/production readiness.

### Docker Desktop not running

Check:

```text
Docker Desktop is open and engine is running.
docker ps works.
```

Fix:

```text
Start Docker Desktop.
Wait for engine ready.
Run docker compose up again.
```

### Migrations not up to date

Check:

```text
Backend logs or /ready migration status.
Current expected migration head from Phase 3 evidence: 00022_platform_admin_role.
```

Fix:

```text
Use the existing local migration procedure from the runbook/evidence.
Do not create or edit migrations during this walkthrough.
```

### Stale frontend build/cache

Check:

```text
Browser cache/localStorage.
Old frontend container/image still running.
```

Fix:

```text
Hard refresh browser.
Clear localhost site data.
Restart frontend container.
Rebuild only if the existing runbook says to for local demo replay.
```

### Port conflicts

Check common ports:

```text
3000 frontend
8000 backend
5432 Postgres container binding if used
5678 n8n
6379 Redis if cache profile is used
```

Fix:

```text
Stop the conflicting local process or adjust local-only ports with explicit approval.
Do not change committed config for the walkthrough.
```

---

## 6. QA checklist

Use this pass/fail table during the boss demo.

| Check | PASS / FAIL | Notes |
|---|---:|---|
| Git status clean before demo |  |  |
| Local stack starts with `docker compose up` |  |  |
| Login page loads |  |  |
| Demo login works |  |  |
| Dashboard loads |  |  |
| Contacts/prospects page loads |  |  |
| Campaign flow works |  |  |
| Draft generation/open draft works |  |  |
| Evidence/grounding view is visible where supported |  |  |
| Review queue loads |  |  |
| Human approval action works |  |  |
| Send-gate dry run works |  |  |
| Mock send intent works |  |  |
| Outbound message record is visible |  |  |
| Audit record is visible |  |  |
| Billing/access gates are visible |  |  |
| Suppression/compliance page or gate behavior is visible |  |  |
| Deliverability dashboard loads |  |  |
| Outcomes dashboard loads |  |  |
| Stripe checkout/portal fail closed |  |  |
| No real provider action happens |  |  |
| Logout works |  |  |
| Sign in again works |  |  |
| No unexpected 500 errors during walkthrough |  |  |
| Logs show no secret leakage |  |  |
| William understands what is ready vs blocked |  |  |

Demo passes when the core path works and all live-provider safety checks remain disabled/fail-closed.

---

## 7. Boss-facing close

Use this close at the end of the walkthrough.

### What is ready

- Local/mock MVP browser demo.
- Demo login.
- Dashboard and core workflow views.
- Campaign, draft, review, send gate, mock outbound, audit, billing-gate, compliance, deliverability, and outcomes demo flow.
- Safety gates proving no live email, no live billing, and no production environment.

### What is blocked

- Staging deployment.
- AWS provisioning.
- Registry/image publishing.
- Real Clerk staging auth.
- Stripe test-mode smoke.
- Resend transactional internal smoke.
- Cold outreach live sending.
- SMS/live scraping.
- Production launch.

### What William needs to approve next

Based on P4-1b, William should provide or approve:

1. AWS account ID and region.
2. Staging runtime config path and KMS ownership.
3. Registry target and push approver.
4. Staging frontend/API domains and DNS/TLS owner.
5. Clerk staging values or explicit limited mock-staging approval.
6. Migration, deployment, rollback approvers, and alert recipients.

### Recommended next approval path

Recommended order:

1. Review and approve the local/mock demo.
2. Lock AWS account/region, config/KMS path, and staging domains.
3. Start P4-2 staging path and config contract only after values are LOCKED or explicitly DEFERRED.
4. Do not jump to deployment. P4-5 remains blocked until platform, domains, secrets/config, registry, RDS/Redis, approvers, and alerts are locked.

Suggested final sentence:

> The local/mock MVP is ready for review. The next real progress is not more coding yet — it is William locking the staging and operator values so Phase 4 implementation can safely begin.

---

## 8. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only intended docs are changed/added. |
| Changed-file scope | PASS — no backend, frontend, app config, migration, `.env`, Dockerfile, workflow, package, or test files changed. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Provider SDK/API calls | PASS by scope — docs-only changes; no code or package files changed. |
| Safety boundary | PASS — P4-Demo-Walkthrough creates a script/checklist only. No code changes, AWS provisioning, deployment, image push, live provider enablement, real billing, production enablement, SMS, or live scraping. |

---

## 9. Final verdict

- P4-Demo-Walkthrough script created.
- Local/mock boss demo is ready to run using existing Phase 3 evidence.
- Implementation remains blocked until owner/operator values are LOCKED or explicitly DEFERRED.
- No code changes, deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping enabled.
