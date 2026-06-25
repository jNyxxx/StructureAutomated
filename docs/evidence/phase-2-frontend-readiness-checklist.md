# Phase 2 Frontend Readiness Checklist

**Date:** 2026-06-25
**Scope:** Phase 2 frontend read-only wiring
**Runtime:** Local/mock only
**Production status:** Not approved

## Read-only wiring checklist

| Area | Status | Evidence |
|---|---:|---|
| Backend mock API read wiring | Pass | FE-P2-1 through FE-P2-7b completed and pushed. |
| Fixture fallback | Pass | Fallback tests cover backend unavailable paths for major surfaces. |
| Local/mock notices | Pass | `LocalMockNotice` remains rendered on local/mock product pages. |
| Gate badges | Pass | `GateReasonBadge` remains used for blocked, warning, pending, and read-only states. |
| Disabled actions | Pass | Mutation actions remain disabled or hidden behind locked row actions. |
| Backend gates source of truth | Pass | Frontend only displays safe read state; backend remains authoritative for access and gates. |
| Production claims | Pass | No production readiness or production activation claim added. |

## Surface checklist

| Surface | Read-only endpoint coverage | Disabled/deferred actions |
|---|---|---|
| Billing / usage | Subscription, access, usage reads | Stripe checkout, payment data, billing state transitions. |
| Settings / tenant / team / audit | Current tenant, memberships, audit reads | Invite/remove/change-role/security/support mutations, audit export/raw delete. |
| Compliance / suppressions | Compliance profile and suppression reads | Compliance PUT, suppression POST, reinstate, export, legal automation. |
| Prospects / contacts | Prospect list, contact list/detail reads | Import persistence, enrichment, live scraping, delete, export, campaign add. |
| Campaigns | Campaign list/detail reads | Create/update/contact selection/run/research/export. |
| Draft detail / evidence | Draft detail and evidence reads | Generate/regenerate, approve, send, provider AI calls. |
| Review queue | Review item list/detail reads | Approve/reject/request-regeneration/send actions. |
| Deliverability | Deliverability dashboard and mailbox/domain reads | Provider sync, DNS verification, warmup, sending, webhooks, export/recalc. |
| Outcomes / ROI | Outcomes and ROI reads | Mock-event POST, export/sync/recalc, CRM/ad/provider/Stripe integrations. |

## Final verification checklist

| Check | Status | Result |
|---|---:|---|
| Git clean before final verification | Pass | `HEAD = origin/master = f8e1f2e` after FE-P2-7b commit/push. |
| Lock-file check | Pass | No `.git` lock files listed. |
| Concurrent writer/test check | Pass | No active matching writer/test process detected. |
| Backend lint | Pass | `python -m ruff check app tests`. |
| Backend format check | Pass | `python -m black --check app tests`. |
| Backend typecheck | Pass | `python -m mypy app --ignore-missing-imports`. |
| Backend tests | Pass | `python -m pytest`: 511 passed, 1 warning. |
| Frontend lint | Pass | `npm run lint`. |
| Frontend typecheck | Pass | `npm run typecheck`. |
| Frontend tests | Pass | `npm run test`: 85 passed. |
| Frontend build | Pass | `npm run build`: compiled and generated 27 static pages. |
| OpenAPI path count | Pass | 44 paths exposed. |
| Safety wording audit | Pass | Unsafe enablement claims not found; blocked/deferred wording remains visible. |

## Required guardrails still active

- Local/mock only.
- Backend mock APIs only for read surfaces.
- Backend remains source of truth for gates.
- Write/mutation actions remain disabled/deferred.
- Real providers are deferred.
- Production is not approved.
- Live DB smoke remains deferred unless separately authorized and available.
- Privacy export/delete/vector purge remains deferred because the backend workflow is not implemented.
- Phase 3 requires explicit owner approval.

## Not ready for production

This checklist does not approve production. Before production, owner approval and separate production readiness work are still required, including real provider decisions, production billing, live DB smoke, legal/compliance review, privacy export/delete workflow, production observability, backup/restore drill, and deployment hardening.
