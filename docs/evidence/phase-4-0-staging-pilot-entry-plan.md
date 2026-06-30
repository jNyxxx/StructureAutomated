# Phase 4-0 — Staging and First-Pilot Entry Plan

**Purpose:** Open Phase 4 safely with a docs-only staging and first-paying-client pilot entry plan.
**Slice:** P4-0
**Date:** 2026-06-30
**Status:** Complete — docs-only. No deployment, no AWS provisioning, no registry push, no live providers, no production launch.
**Base commit:** `fea2c03 docs(p3): correct final handoff commit references`
**Related docs:** [PHASE_4_IMPLEMENTATION_PLAN](../PHASE_4_IMPLEMENTATION_PLAN.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md) · [DOCUMENTATION_MANIFEST](../DOCUMENTATION_MANIFEST.md)

---

## 1. Preflight result

| Check | Result |
|---|---|
| `git fetch origin` | PASS |
| `git status --short` before edits | PASS — clean |
| `git log --oneline -25` | PASS — latest `fea2c03 docs(p3): correct final handoff commit references` |
| `git ls-remote origin refs/heads/master` | PASS — `fea2c03c6e6a122a432dfacc2ac97abf99e99c25` |
| `HEAD = origin/master` | PASS — both `fea2c03c6e6a122a432dfacc2ac97abf99e99c25` |
| `.git` lock files | PASS — none found |
| Concurrent writer / agent / test process | PASS — none found |

---

## 2. Codebase and documentation scan

High-level repo state:

| Area | Current state |
|---|---|
| Backend | Tracked backend implementation exists; Phase 3 audit previously recorded Ruff/Black/mypy/731 pytest PASS. No backend files changed in P4-0. |
| Frontend | Tracked Next.js frontend exists; Phase 3 audit previously recorded npm ci/lint/typecheck/141 vitest/build PASS. No frontend files changed in P4-0. |
| Docs | Phase 0, Phase 1, Phase 2, and Phase 3 plans/evidence exist. P4-0 adds Phase 4 plan/evidence and updates planning trackers only. |
| Local/mock demo | Ready per P3-Final and P3-Audit. Mock browser demo remains the only approved runnable path. |
| Staging / providers / production | Still blocked on owner/operator values. No deployment, registry push, provider smoke, live billing, SMS, or live scraping in P4-0. |

Files inspected for P4-0:

- `docs/evidence/phase-3-final-boss-handoff-package.md`
- `docs/evidence/phase-3-final-requirements-architecture-audit.md`
- `docs/evidence/phase-3-8a-launch-readiness-dashboard.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/DOCUMENTATION_MANIFEST.md`
- `docs/STAGING_ENVIRONMENT_TEMPLATE.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`
- `docs/AUTH_AND_RBAC.md`
- `docs/BILLING_STATE_MACHINE.md`
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md`

---

## 3. Phase 4 scope

Phase 4 is scoped to staging deployment preparation and first paying-client pilot readiness. It includes Clerk staging auth, Stripe test-mode billing smoke, transactional Resend internal smoke, staging smoke evidence, monitoring/alerts, rollback readiness, and a first-pilot review.

Phase 4 does not approve public production launch.

---

## 4. Phase 4 non-goals

P4-0 and Phase 4 planning do not approve production launch, live cold outreach, live billing or money movement, SMS, live scraping, public self-serve launch, cold-sending domains before mailbox-pool approval, boot-guard weakening, auth/RBAC/RLS bypass, billing/send-gate bypass, real credential commits, AWS provisioning, registry push, or deployment.

---

## 5. Required owner/operator values

Phase 4 requires owner/operator values across these groups before implementation slices can proceed:

- AWS account/region and platform choice.
- ECR/registry target and image-push approval.
- Staging frontend/API domains and DNS/TLS owner.
- Staging runtime config paths, KMS/encryption ownership, and injection method.
- RDS/Postgres config, app/runtime role, migration role, backups, and restore-drill owner.
- Redis/ElastiCache config and rate-limit readiness owner.
- Clerk staging project, issuer/JWKS/audience/AZP/MFA claim, publishable key, backend key path, and tenant-selector decision.
- Stripe test key path, webhook signing path, test price IDs, smoke approver, billing owners, and emergency-stop owner.
- Resend transactional key path, webhook signing path, DNS proof, sender/Reply-To, legal footer values, internal recipient, smoke approver, deliverability owner, and emergency-stop owner.
- Alert recipients, escalation owner, incident recorder, and retention owner.
- Deployment, migration, rollback, release-evidence, first-pilot, onboarding, support, and later production-cutover approvers.

---

## 6. Proposed Phase 4 slices

| Slice | Summary |
|---|---|
| P4-1 | Staging infrastructure values lock. |
| P4-2 | Staging path and config contract. |
| P4-3 | Clerk staging integration. |
| P4-4 | Registry/image publishing pipeline. |
| P4-5 | Staging deployment implementation. |
| P4-6 | Staging smoke evidence. |
| P4-7 | Stripe test-mode smoke. |
| P4-8 | Transactional Resend internal smoke. |
| P4-9 | Monitoring/alerts readiness. |
| P4-10 | First-pilot readiness review. |

## 7. Entry criteria

P4-0 confirms Phase 4 may open for planning because Phase 3 final handoff is complete, P3-Audit passed, handoff commit references were corrected, local/mock demo is verified, boss review can proceed, live providers remain disabled, billing remains mock/fail-closed, and open blockers are recorded.

## 8. Exit criteria

Phase 4 should exit only after approved staging deploy, passing staging smoke, Clerk staging auth or approved limited mock-staging auth, optional approved Stripe test-mode smoke, optional approved transactional Resend internal smoke, monitoring/alerts test, rollback path test, first-pilot checklist approval, and no production cutover unless Phase 5 is approved.

## 9. Hard stop conditions

Hard stops include missing owner values, missing rollback owner, missing alert recipients, real credentials in repo, unexpected production cutover, live email send path without smoke approval, cold outreach reaching a live provider, Stripe live mode before approval, billing mutation before design approval, SMS/live scraping activation, boot-guard weakening, RLS/RBAC/tenant isolation bypass, billing/send-gate bypass, registry push or deployment during P4-0, or accepting failed smoke without owner risk acceptance.

## 10. Files changed

| File | Action |
|---|---|
| `docs/PHASE_4_IMPLEMENTATION_PLAN.md` | Created Phase 4 plan. |
| `docs/evidence/phase-4-0-staging-pilot-entry-plan.md` | Created P4-0 evidence. |
| `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md` | Updated with P4-0 verdict and Phase 4 owner/operator values. |
| `docs/OPERATIONS_RUNBOOK.md` | Updated with P4-0 staging/pilot runbook note. |
| `docs/DOCUMENTATION_MANIFEST.md` | Updated with Phase 4 plan and evidence entries. |

## 11. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only the five intended docs are changed/added. |
| Changed-file scope | PASS — no backend, frontend, app config, migration, `.env`, Dockerfile, workflow, package, or test files changed. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Provider SDK/API calls | PASS by scope — docs-only changes; no code or package files changed. |
| Safety boundary | PASS — P4-0 does not approve AWS provisioning, deployment, live sending, cold outreach, billing money movement, SMS, or live scraping. |

## 12. Final verdict

- Phase 4-0 complete.
- Phase 4 opened safely for planning.
- No deployment or live provider enablement approved by P4-0.

---
