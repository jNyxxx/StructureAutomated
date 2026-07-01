# Phase 4 Implementation Plan

**Purpose:** Open Phase 4 safely as the staging and first-paying-client pilot readiness program.
**Source sections:** Phase 3 final handoff, P3-Audit, P3-8a launch readiness dashboard, staging environment template, launch blockers, operations runbook.
**Status:** Draft — Phase 4-0 planning complete; no deployment, no real providers, no production launch.
**Related docs:** [STAGING_ENVIRONMENT_TEMPLATE](STAGING_ENVIRONMENT_TEMPLATE.md) · [OPERATIONS_RUNBOOK](OPERATIONS_RUNBOOK.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md)

---

## 1. Phase 4 definition

Phase 4 is the controlled transition from a local/mock demo-ready product to a staging-backed, first-pilot-ready product.

Phase 4 does not approve public launch. It prepares the staging environment, validates staging smoke evidence, and records owner/operator approvals needed before the first paying-client pilot.

Phase 4 starts with P4-0: this staging and first-pilot entry plan. P4-0 is docs-only.

## 2. Phase 4 scope

Phase 4 includes staging deployment preparation, first paying-client pilot readiness planning, Clerk staging auth, Stripe test-mode billing smoke, transactional Resend internal smoke, staging smoke evidence, monitoring and alerts, migration/rollback evidence, and first-pilot go/no-go review.

No public production launch is approved by Phase 4.

## 3. Phase 4 non-goals

Phase 4 excludes public production launch, live cold outreach, live Stripe billing or money movement without explicit later approval, SMS, live scraping, public self-serve launch, cold-sending domains before mailbox-pool approval, boot-guard weakening, auth/RBAC/RLS/tenant-isolation bypass, billing/send-gate bypass, real credentials in Git, registry push, AWS provisioning, or deployment during P4-0.

## 4. Required owner/operator values

Phase 4 implementation slices cannot proceed until the relevant owner/operator values are supplied and recorded.

| Track | Required values |
|---|---|
| AWS / platform | AWS account ID, region, deployment platform, VPC/networking owner, environment naming. |
| Registry | ECR/registry target, image naming, immutable tag policy, push approver. |
| Domains / TLS | Staging frontend domain, staging API domain, DNS owner, TLS owner, certificate validation, CORS/cookie domain policy. |
| Staging config custody | Environment path convention, encryption key alias/ARN, runtime injection method, rotation owner, access-review owner. |
| RDS / Postgres | Engine/version, instance class, storage, VPC/subnet/security group, app runtime role, migration role, backup retention, snapshot policy, restore-drill owner. |
| Redis / ElastiCache | Instance class, TLS setting, VPC/subnet/security group, Redis URL path, rate-limit readiness owner. |
| Clerk staging | Clerk staging project, publishable key, issuer URL, JWKS URL, audience, authorized parties/AZP, MFA claim/JWT template, backend key path, tenant-selector decision. |
| Stripe test mode | Test backend key path, webhook signing path, test product/price IDs, webhook endpoint URL, smoke approver, billing-state owner, billing-portal owner, emergency-stop owner. |
| Resend transactional smoke | Provider key path, webhook signing path, SPF/DKIM/DMARC proof, sender identity, monitored Reply-To inbox, legal footer/company mailing details, internal smoke recipient, smoke approver/window, deliverability owner, emergency-stop owner. |
| Monitoring / alerts | Alert recipients/channels, escalation owner, severity policy, on-call window, incident recorder, log/trace retention owner. |
| Deployment / migration / rollback | Deployment approver, migration approver, rollback approver, previous-image retention policy, DB snapshot/restore owner, release evidence owner. |
| Pilot / cutover | First-pilot tenant owner, onboarding approver, support/escalation owner, production cutover approver for later Phase 5. |

## 5. Proposed Phase 4 slices

| Slice | Name | Class | Acceptance / stop gate |
|---|---|---|---|
| P4-0 | Staging and first-pilot entry plan | docs / planning | Create plan and evidence, update launch blockers/runbook/manifest. No deployment, provider enablement, AWS work, registry push, credentials, or code changes. |
| P4-1 | Staging infrastructure values lock | planning / owner-values | **Complete as intake packet only.** Required owner/operator values are recorded as MISSING/PROPOSED/LOCKED; no values are locked yet, so P4-2/P4-4/P4-5 remain blocked. See [evidence/phase-4-1-staging-infrastructure-values-intake.md](evidence/phase-4-1-staging-infrastructure-values-intake.md). |
| P4-1b | Owner response tracker and decision matrix | docs / planning | **Complete as tracker only.** Records future William/operator answers using MISSING/PROPOSED/LOCKED/DEFERRED states and maps each answer to the next allowed Phase 4 slice. Implementation remains blocked until required values are LOCKED or explicitly DEFERRED. See [evidence/phase-4-1b-owner-response-tracker.md](evidence/phase-4-1b-owner-response-tracker.md). |
| P4-Demo-Walkthrough | Boss demo walkthrough script and QA checklist | docs / demo-readiness | **Complete as docs-only demo support.** Creates a clean local/mock boss walkthrough, safety proof, troubleshooting guide, and pass/fail QA checklist. Does not unblock implementation. See [evidence/phase-4-demo-walkthrough-script.md](evidence/phase-4-demo-walkthrough-script.md). |
| P4-DepAudit-Plan | Dependency audit triage plan | docs / security planning | **Complete as docs-only triage.** Records npm audit evidence, classifies findings, defines future fix slices, and confirms no package changes or automatic fixes were applied. Boss demo remains allowed; staging/production require fixes or explicit risk acceptance. See [evidence/phase-4-dependency-audit-triage-plan.md](evidence/phase-4-dependency-audit-triage-plan.md). |
| P4-DepAudit-Fix-1 | Safe targeted dev dependency fixes | frontend package maintenance | **Complete.** Updated `vitest` to `3.2.6` and pinned `vite` to `6.4.3` for dev/test tooling only. Critical audit finding cleared; audit reduced 10 → 5. Next.js runtime and Next ESLint/glob findings remain. Boss demo allowed; staging/production still blocked. See [evidence/phase-4-dependency-audit-fix-1.md](evidence/phase-4-dependency-audit-fix-1.md). |
| P4-DepAudit-Fix-2 | Controlled remaining frontend dependency audit fixes | dependency assessment | **BLOCKED.** No same-major compatible fix exists for the remaining Next.js runtime/PostCSS and Next lint-chain findings. No package changes were made. P4-DepAudit-Fix-3 framework upgrade planning is required unless owner/security formally accepts the remaining findings. See [evidence/phase-4-dependency-audit-fix-2.md](evidence/phase-4-dependency-audit-fix-2.md). |
| P4-DepAudit-Fix-3-Plan | Framework upgrade approval and migration plan | docs / approval planning | **Complete as docs-only plan.** Recommends owner-approved Next 15 controlled upgrade attempt first, with Next 16 escalation only if needed or explicitly approved. No package/source/config changes. Boss demo allowed; staging/production still blocked. See [evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md](evidence/phase-4-dependency-audit-fix-3-framework-upgrade-plan.md). |
| P4-FirstPilot-Readiness | First paying-client readiness checklist | docs / pilot planning | **Complete as docs-only checklist.** Defines limited pilot scope, required pre-client evidence, onboarding fields, demo-to-pilot gaps, go/no-go criteria, hard stops, and required William approvals. Boss demo allowed; staging/production still blocked. See [evidence/phase-4-first-pilot-readiness-checklist.md](evidence/phase-4-first-pilot-readiness-checklist.md). |
| P4-Monitoring-Alerts-Plan | Monitoring, alerts, incident ownership, and rollback plan | docs / ops planning | **Complete as docs-only plan.** Defines staging-first monitoring scope, alert categories, owners, SEV levels, staging smoke observability, rollback plan, hard stops, and William-facing questions. Boss demo allowed; staging/production still blocked. See [evidence/phase-4-monitoring-alerts-incident-plan.md](evidence/phase-4-monitoring-alerts-incident-plan.md). |
| P4-LocalReadiness-Closeout / Resume | Final local readiness, QA, demo, and first-client prep package | docs / local hardening closeout | **Complete after resume.** Initial closeout attempt was partial because the devspace session terminated before tracking-doc updates, verification, commit, and push. Resume finalized the docs-only closeout package. Records William's pause on AWS/staging/deployment/registry/provider setup, production waiting for first real client, local hardening/docs/QA continuing, backend gates passing, frontend gates passing except known `master` npm audit, route smoke passing, send-gate/compliance/fail-closed QA, first-client onboarding runbook, and known blockers. Boss demo allowed; manual browser click-through still recommended; `p4/next15-upgrade` remains unmerged until William approves. See [evidence/phase-4-local-readiness-closeout.md](evidence/phase-4-local-readiness-closeout.md), [evidence/phase-4-sendgate-compliance-qa.md](evidence/phase-4-sendgate-compliance-qa.md), and [evidence/phase-4-first-client-onboarding-runbook.md](evidence/phase-4-first-client-onboarding-runbook.md). |
| P4-LocalE2E-Completion | Local full-stack end-to-end completion and hardening | local E2E / QA evidence | **BLOCKED.** Backend gates pass; frontend `npm ci`, lint, typecheck, 141 tests, and build pass; local route smoke passes for core demo routes; API/route inventory confirms frontend/backend surfaces align for the local MVP. No code fixes were applied. Blockers remain: Docker compose cannot be verified because Docker Desktop/Linux daemon is unavailable, `/health`/`/live`/`/ready` through compose were not run, and `npm audit` still fails on `master` until William approves merging `p4/next15-upgrade`. Boss demo allowed with caveats; staging/production remain paused. See [evidence/phase-4-local-e2e-completion.md](evidence/phase-4-local-e2e-completion.md). |
| P4-LocalDockerE2E-Retry | Local Docker full-stack E2E verification retry | local Docker / browser smoke evidence | **BLOCKED.** Docker Desktop/Linux engine is now available and compose build/start passed. DB is healthy; backend, frontend, n8n, and worker containers are up; backend `/health`, `/live`, and `/ready` pass; frontend route smoke passes for all required routes. Full Docker happy-path E2E is still blocked because `POST /api/v1/campaigns` returns 500 in the backend write path (`campaign_repo.py` maps a UUID as a row). No source fix was applied because this requires a separate source-fix slice. Boss demo remains allowed only with caveats; staging/production remain paused. See [evidence/phase-4-local-docker-e2e-retry.md](evidence/phase-4-local-docker-e2e-retry.md). |
| P4-2 | Staging path and config contract | planning / config contract | Finalize staging config matrix from `STAGING_ENVIRONMENT_TEMPLATE.md`. No values in Git. Stop if ownership is missing. |
| P4-3 | Clerk staging integration | staging auth | Wire and smoke Clerk staging after values exist. Preserve mock local demo. Stop if tenant selector or MFA claim is missing. |
| P4-4 | Registry / image publishing pipeline | release plumbing | Add approved image-publish path with immutable tags and approvals. Stop if registry target or push approver is missing. |
| P4-5 | Staging deployment implementation | staging deploy | Deploy only to approved staging platform. Stop if rollback owner, migration approver, alert recipients, RDS, Redis, domains, or runtime injection path are missing. |
| P4-6 | Staging smoke evidence | evidence / QA | Record health, readiness, migration head, auth, tenant isolation, billing gates, send gate, mock campaign, audit, and rollback-readiness evidence. |
| P4-7 | Stripe test-mode smoke | provider smoke / billing | Test mode only after paths and smoke approval. No live mode or money movement. Stop on signature or config failures. |
| P4-8 | Transactional Resend internal smoke | provider smoke / transactional only | One internal-approved email only after DNS/legal/path/recipient/emergency-stop/deliverability values exist. No cold outreach. |
| P4-9 | Monitoring / alerts readiness | ops / incident readiness | Test alert recipients, logs/traces, dependency alerts, incident response, and escalation. Stop if no alert recipient or owner exists. |
| P4-10 | First-pilot readiness review | go/no-go / owner review | Confirm staging, smoke, rollback, legal, auth, billing, transactional email, monitoring, and pilot checklist. Production remains blocked unless Phase 5 is separately approved. |

## 6. Phase 4 entry criteria

- Phase 3 final boss handoff package is complete.
- Phase 3 final requirements/architecture audit passed.
- Phase 3 handoff references were corrected.
- Local/mock demo is verified and preserved.
- P3-Audit allows Phase 4 planning only.
- Boss review is scheduled or completed.
- Real sending remains disabled.
- Real billing remains disabled.
- No deployment, registry push, or production cutover has occurred.
- SMS and live scraping remain disabled.
- Open blockers and owner values are recorded.

Current P4-0 assessment: entry criteria are satisfied for planning only.

## 7. Phase 4 exit criteria

- Staging is deployed to the approved staging platform.
- Staging smoke passes and evidence is attached.
- Clerk staging auth works end-to-end, or an owner-approved mock-staging-auth exception is recorded for a limited smoke.
- Stripe test-mode smoke completes if approved.
- Transactional Resend internal smoke completes if approved.
- Monitoring and alerts are tested.
- Migration and rollback path are tested or explicitly bounded with owner-approved rollback limits.
- Backup/restore plan is recorded and restore drill is scheduled or completed based on production proximity.
- First-pilot checklist is approved.
- Production remains blocked unless Phase 5 is separately approved.

## 8. Hard stop conditions

Stop immediately if required owner/operator values are missing; rollback owner is missing; migration approver is missing; alert recipients are missing; real credentials appear in the repo; production cutover is turned on unexpectedly; a live email provider can send without the approved smoke gate; cold outreach can reach a live provider; Stripe live mode appears before separate approval; billing state mutation is wired before approved design; SMS or live scraping is activated; boot guard is weakened; RLS/RBAC/tenant isolation/object ownership/billing gates/send gates/idempotency/suppression/audit are bypassed; registry push or deployment is attempted in P4-0; or a staging smoke failure is accepted without owner risk acceptance.

## 9. Verification required for every Phase 4 slice

Every Phase 4 slice must record preflight, exact files changed, safety confirmation, relevant gates or evidence checks, unsafe-claim grep results, credential-pattern grep results, changed-file scope, rollback/emergency-stop owner status when relevant, commit hash, and push result.

P4-0 verification is recorded in [evidence/phase-4-0-staging-pilot-entry-plan.md](evidence/phase-4-0-staging-pilot-entry-plan.md).
P4-1 verification is recorded in [evidence/phase-4-1-staging-infrastructure-values-intake.md](evidence/phase-4-1-staging-infrastructure-values-intake.md).
P4-1b verification is recorded in [evidence/phase-4-1b-owner-response-tracker.md](evidence/phase-4-1b-owner-response-tracker.md).

## 10. P4-1 / P4-1b status

P4-1 created the staging infrastructure values intake and lock packet. P4-1b created the owner-response tracker and decision matrix. Current result: staging deployment remains blocked because account, region, registry target, staging domains, DNS/TLS owner, RDS/Redis sizing, release approvers, alert recipients, and staging auth mode are not LOCKED. Safe defaults are recommendations only. P4-2/P4-3/P4-4/P4-5/P4-7/P4-8 are blocked until their required values are LOCKED or explicitly accepted as DEFERRED.

## 11. Final P4-0 / P4-1 verdict

P4-0 opens Phase 4 safely as a planning-only slice. No deployment, live provider, billing money movement, registry push, real credential, SMS, or live scraping is approved by this document.
