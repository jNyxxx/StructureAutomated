# P4-FirstPilot-Readiness — First Paying-Client Readiness Checklist

**Purpose:** Define exactly what must be true before onboarding the first real paying-client pilot.
**Slice:** P4-FirstPilot-Readiness
**Date:** 2026-07-01
**Status:** Complete — docs-only checklist. No code, package, config, secret, deployment, provider, billing, or production change.
**Base commit:** `477d577 docs(p4): plan framework dependency audit upgrade`

---

## 1. Pilot scope

The first paying client is a limited, controlled pilot. It is not a public launch.

Pilot rules:

- The pilot must run only after staging has passed smoke evidence and William approves pilot entry.
- AI-generated drafts require manual human approval before any outbound action.
- Cold outreach remains mock/live-disabled unless a separate owner-approved cold outreach path exists.
- Transactional email smoke remains separate from cold outreach.
- Stripe live money movement remains blocked unless a separate billing launch approval exists.
- SMS and live scraping remain disabled.
- Production remains blocked until a later go/no-go decision.

---

## 2. Required before first client

| Requirement | Status now | Required evidence before pilot |
|---|---|---|
| Staging environment | BLOCKED | Staging environment available on the approved platform and smoke-tested. |
| Dependency audit | BLOCKED | Remaining findings fixed or formally owner/security risk-accepted. |
| Next.js framework upgrade | WAITING OWNER APPROVAL | P4-DepAudit-Fix-3a approved and completed, or risk acceptance recorded. |
| Clerk staging/auth | BLOCKED | Clerk staging values locked and auth smoke passed, or explicitly approved limited staging auth mode. |
| Tenant creation process | REQUIRED | Written tenant creation/runbook with tenant owner, role assignment, billing state, and audit record. |
| Billing/access gates | REQUIRED | Trial/active/past-due/canceled/inactive gates verified for the pilot tenant. |
| Send gates | REQUIRED | Dry-run and actual allowed/blocked paths verified in staging. |
| Suppression/compliance | REQUIRED | Suppression, unsubscribe, compliance jurisdiction, and footer policy verified. |
| Audit trail | REQUIRED | Login, campaign, draft review, gate, billing, and admin actions leave audit records. |
| Rollback owner | MISSING | Named rollback owner and approval rule recorded. |
| Support/incident owner | MISSING | Named support owner, incident owner, escalation path, and contact window recorded. |
| Monitoring/alerts | MISSING | Alert recipients, dashboard/log target, and incident notification test verified. |
| Emergency stop owner | MISSING | Named operator who can stop sending/provider/billing smoke paths. |
| Legal/compliance approval | REQUIRED | Pilot jurisdiction and client-facing notices approved. |

---

## 3. Client onboarding checklist

Complete one copy of this table for each pilot client.

| Field | Required value before onboarding |
|---|---|
| Client name | Legal/business display name. |
| Legal entity | Contracting legal entity or registered business name. |
| Tenant owner email | Primary owner account email. |
| Users and roles | Owner/admin/member/viewer list with least-privilege role assignment. |
| Allowed features | Exact enabled modules for the pilot tenant. |
| Billing state | Initial mock/test/manual billing state and access gates. |
| Compliance jurisdiction | Applicable jurisdiction and approved policy baseline. |
| Sending policy | Whether outbound is mock-only, transactional-only, or separately approved. |
| Suppression/unsubscribe policy | Seed suppressions, unsubscribe handling, and do-not-contact rules. |
| Support contact | Client-side support contact and internal support owner. |
| Emergency stop contact | Internal operator who can stop risky flows. |
| Data source approval | Which client data sources may be imported or connected. |
| Data retention note | Retention/export/delete expectations for the pilot. |
| Evidence owner | Person responsible for pilot evidence bundle. |

---

## 4. Demo-to-pilot gap list

### Works locally/mock today

- Local/mock browser demo login.
- Dashboard and core MVP navigation.
- Campaign/contact/prospect demo flow.
- Draft/evidence/review queue surfaces.
- Human review and send-gate dry-run flow.
- Mock send intent and outbound/audit records.
- Billing/access-gate UI and mock states.
- Compliance/suppression UI.
- Deliverability/outcomes demo dashboards.
- Production-shaped Docker builds from prior Phase 3 evidence.

### Must be real before pilot

- Staging platform, domain, TLS, config custody, and smoke evidence.
- Clerk staging auth or explicitly approved limited staging auth mode.
- Dependency audit closure or formal risk acceptance.
- Tenant creation and onboarding runbook.
- Pilot tenant billing/access-gate evidence.
- Monitoring, alerts, incident, rollback, and emergency-stop ownership.
- Legal/compliance approval for the pilot scope.
- Client-specific data/source permissions.

### Intentionally disabled unless separately approved

- Public production launch.
- Live cold outreach.
- Stripe live money movement.
- SMS.
- Live scraping.
- Self-serve public onboarding.
- Unapproved provider integrations.
- Any bypass of auth, RBAC, RLS, billing gates, send gates, suppression, or audit.

---

## 5. Go/no-go criteria

### GO criteria

The pilot can proceed only when all are true:

- William approves first-pilot entry in writing.
- Staging smoke passes and evidence is linked.
- Remaining dependency findings are fixed or formally accepted.
- Clerk staging/auth path is approved and verified.
- Pilot tenant is created with correct owner, users, roles, and billing/access state.
- Billing/access gates pass expected pilot scenarios.
- Send gates and suppression/compliance checks pass expected pilot scenarios.
- Monitoring/alerts are verified.
- Rollback, support, incident, and emergency-stop owners are named.
- Client onboarding checklist is complete.
- Production remains blocked unless separately approved.

### NO-GO criteria

Do not onboard the first real client if any are true:

- William has not approved the pilot.
- Staging smoke is missing or failed.
- Dependency findings remain unresolved without risk acceptance.
- Clerk/auth path is not verified.
- Tenant creation process is not documented.
- Billing/access or send-gate behavior is unclear.
- Suppression/compliance policy is missing.
- Audit trail is incomplete for risky actions.
- Rollback owner, alert recipients, or support owner are missing.
- Any live/provider/payment mode is active without explicit approval.
- Production is selected accidentally.

Required William approvals:

- First-pilot entry approval.
- Dependency risk/fix approval.
- Auth mode approval.
- Staging go/no-go approval.
- Client onboarding approval.
- Any separate live-provider or billing approval if that scope is requested.

---

## 6. Hard stops

Stop immediately if any condition occurs:

- no owner approval;
- no staging smoke evidence;
- dependency findings unresolved and not formally accepted;
- no rollback owner;
- no alert recipients;
- live sending becomes active unexpectedly;
- Stripe live mode appears unexpectedly;
- production environment is selected accidentally;
- RLS, RBAC, tenant isolation, billing gates, or send gates are weakened;
- suppression or unsubscribe handling is bypassed;
- audit records are missing for risky actions;
- secrets or client-sensitive values are committed;
- SMS or live scraping is activated.

---

## 7. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS. |
| `git status --short` | PASS — only intended docs changed before commit. |
| Package/source/config scope | PASS — no package, backend, frontend source, config, `.env`, Dockerfile, workflow, or deployment file changes. |
| Unsafe-claim grep | PASS — only pre-existing Phase 4 exit-criteria wording was found; no new active-state claim was added. |
| Secret-pattern check | PASS. |
| Registry/deployment activity | PASS — none performed. |
| Safety boundary | PASS — docs-only first-pilot checklist. |

---

## 8. Final verdict

- P4-FirstPilot-Readiness complete.
- Boss demo remains allowed.
- Staging remains blocked.
- Production remains blocked.
- First paying-client pilot is not approved yet.
- Implementation still requires William/owner values and approvals.
