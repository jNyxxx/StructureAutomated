# P4-1b — Owner Response Tracker and Phase 4 Decision Matrix

**Purpose:** Track William's future answers and map each locked/deferred answer to the next allowed Phase 4 slice.
**Slice:** P4-1b
**Date:** 2026-06-30
**Status:** Complete — docs-only tracker. No deployment, AWS provisioning, registry push, real provider enablement, real billing, production enablement, SMS, or live scraping.
**Base commit:** `aa86e33 docs(p4): add staging infrastructure values intake`
**Related docs:** [phase-4-1-staging-infrastructure-values-intake](phase-4-1-staging-infrastructure-values-intake.md) · [PHASE_4_IMPLEMENTATION_PLAN](../PHASE_4_IMPLEMENTATION_PLAN.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md)

---

## 1. Tracker rules

This tracker records owner/operator answers after they are provided. It must not invent values.

Status meanings:

- **MISSING** — no answer has been provided; blocking slice cannot start.
- **PROPOSED** — safe recommendation only; not permission to implement.
- **LOCKED** — owner/operator supplied and approved the answer.
- **DEFERRED** — owner/operator explicitly accepted deferral, with owner, reason, risk, and next review point recorded.

If a value is MISSING or only PROPOSED, the linked slice remains blocked.

---

## 2. Owner response table

| Question / value needed | Current status | Owner | Answer received | Evidence location | Unlocks which slice | Notes / risk |
|---|---|---|---|---|---|---|
| AWS account ID | MISSING | William / DevOps | None | None yet | P4-2, P4-5 | No staging account target; do not configure cloud paths or deploy. |
| AWS region | MISSING | William / DevOps | None | None yet | P4-2, P4-5 | Wrong or missing region can cause service mismatch, cost drift, or compliance issues. |
| Staging runtime config base path | PROPOSED | DevOps / Security | `/automatedstructure/staging/...` proposed only | `STAGING_ENVIRONMENT_TEMPLATE.md` | P4-2 | Recommendation only; must be owner-approved before use. |
| KMS key / alias owner and value | MISSING | DevOps / Security | None | None yet | P4-2 | Runtime config and credential encryption cannot be verified. |
| Secret-injection method | MISSING | DevOps / Security | None | None yet | P4-2, P4-5 | Services may accidentally rely on local files or manual values. |
| ECR / registry target | MISSING | William / DevOps | None | None yet | P4-4 | No image publishing path; do not push images. |
| Registry push approver | MISSING | William / DevOps | None | None yet | P4-4 | Image publishing could happen without approval. |
| Deployment platform | PROPOSED | William / DevOps | ECS/Fargate recommended only | P4-1 intake | P4-5 | Recommendation only; platform must be locked before deploy plan. |
| Staging frontend domain | MISSING | William / DNS/TLS owner | None | None yet | P4-3, P4-5 | Frontend URL, Clerk redirect, cookies, and CORS cannot be finalized. |
| Staging API domain | MISSING | William / DNS/TLS owner | None | None yet | P4-2, P4-3, P4-5 | API base URL, CORS, and smoke evidence cannot be finalized. |
| DNS/TLS owner | MISSING | William | None | None yet | P4-5 | No accountable operator for DNS or certificate incidents. |
| Certificate/TLS approach | MISSING | DNS/TLS owner / DevOps | None | None yet | P4-5 | Staging may lack HTTPS parity or fail Clerk/cookie requirements. |
| RDS/Postgres engine/version | PROPOSED | DevOps / DB owner | PostgreSQL 16-compatible recommended only | `STAGING_ENVIRONMENT_TEMPLATE.md` | P4-5 | Must be locked against migration requirements before staging DB work. |
| RDS class/storage/backup retention | MISSING | DevOps / DB owner | None | None yet | P4-5, P4-10 | Under-sizing or missing backups blocks reliable staging and later production. |
| DB role ownership | MISSING | DevOps / DB owner | None | None yet | P4-5, P4-6 | App role may be unsafe or unowned. |
| Redis/ElastiCache type/size | PROPOSED | DevOps / SRE | Managed Redis recommended only | `STAGING_ENVIRONMENT_TEMPLATE.md` | P4-5, P4-6 | Must be locked for rate-limit parity and readiness. |
| Redis auth/TLS decision | MISSING | DevOps / SRE | None | None yet | P4-2, P4-5 | Redis traffic/config may be insecure or incompatible. |
| Clerk staging publishable key owner | MISSING | William / Auth owner | None | None yet | P4-3 | Frontend cannot complete real auth smoke. |
| Clerk issuer/JWKS/audience/AZP/MFA values | MISSING | William / Auth owner | None | None yet | P4-3 | Backend cannot validate real Clerk staging tokens. |
| Approved staging auth mode if Clerk is not ready | MISSING | William / Security | None | None yet | P4-3, P4-5 | Mock staging auth must be explicitly approved and clearly labeled. |
| Migration approver | MISSING | William / DevOps | None | None yet | P4-5, P4-6 | Schema changes may run without accountable approval. |
| Deployment approver | MISSING | William / DevOps | None | None yet | P4-4, P4-5 | Staging release could happen without authorization. |
| Rollback approver | MISSING | William / DevOps | None | None yet | P4-5, P4-6 | Failed staging release may lack a rollback decision owner. |
| Alert recipients/channel | MISSING | William / Ops | None | None yet | P4-5, P4-6, P4-9 | Incidents and readiness failures may go unnoticed. |
| Incident owner | MISSING | William / Ops | None | None yet | P4-5, P4-9 | No accountable person for incident response. |
| Emergency-stop owner | MISSING | William / Ops | None | None yet | P4-7, P4-8, P4-9 | Provider smoke cannot proceed without an operator who can stop it quickly. |
| Log retention target | MISSING | William / Ops | None | None yet | P4-9 | Evidence may be lost too early or retained too long. |
| Monitoring target | MISSING | William / Ops | None | None yet | P4-9 | No dashboard/log/alert destination is known. |
| Worker command/service decision | MISSING | Engineering / DevOps / William | None | None yet | P4-5, P4-6 | Worker may run the wrong command or remain intentionally disabled. |
| Stripe test refs and smoke approver | MISSING | William / Billing owner | None | None yet | P4-7 later | Test-mode billing smoke cannot start; live mode remains blocked. |
| Resend refs, DNS, legal footer, internal recipient | MISSING | William / Legal / Deliverability owner | None | None yet | P4-8 later | Transactional smoke cannot start; live email remains disabled. |

---

## 3. Decision-to-slice mapping

| Decision locked | Next allowed slice | Notes |
|---|---|---|
| AWS account and region locked | P4-2 may start | Still requires config-path/KMS decisions for complete P4-2 scope. |
| Staging runtime config path and KMS values locked | P4-2 may start | P4-2 remains docs/config-contract only; no secret values in Git. |
| Registry target and push approver locked | P4-4 may start | P4-4 may design/publish pipeline only after approval; no latest-only images. |
| Clerk staging values locked | P4-3 may start | Requires publishable key owner, issuer/JWKS/audience/AZP/MFA claim, and tenant/auth mode decision. |
| Approved mock-staging auth mode locked | P4-3 may start with limited mock path | Must be explicit, labeled, and not misrepresented as real Clerk auth. |
| Stripe test refs plus smoke approver locked | P4-7 may start later | Only after required config contracts and staging path are ready; no live mode or money movement. |
| Resend refs, DNS proof, legal footer, and internal recipient locked | P4-8 may start later | Transactional internal smoke only; no cold outreach. |
| Staging domains plus DNS/TLS owner locked | P4-5 may start later | Also requires platform, config, registry, RDS/Redis, and approvers. |
| Alert recipients plus rollback and migration approvers locked | P4-5/P4-6 may start later | Required for staging deployment and smoke evidence. |

---

## 4. Explicit blocked list

| Slice | Current status | Blocked until |
|---|---|---|
| P4-2 staging path and config contract | BLOCKED | AWS account/region, runtime config path ownership, KMS, and secret-injection decisions are LOCKED or explicitly deferred. |
| P4-3 Clerk staging integration | BLOCKED | Clerk values are LOCKED, or explicit mock-staging approval is LOCKED. |
| P4-4 registry/image publishing pipeline | BLOCKED | Registry target and push approver are LOCKED. |
| P4-5 staging deployment implementation | BLOCKED | Platform, domains, DNS/TLS, config path, RDS/Redis, registry, deployment approver, migration approver, rollback approver, and alert recipients are LOCKED. |
| P4-7 Stripe test-mode smoke | BLOCKED | Stripe test refs and named smoke approver are LOCKED; live billing remains blocked. |
| P4-8 transactional Resend internal smoke | BLOCKED | Resend refs, DNS proof, legal footer, monitored Reply-To, internal recipient, deliverability owner, and emergency-stop owner are LOCKED. |

---

## 5. Safe work list while blocked

While owner/operator values remain MISSING or PROPOSED, safe work is limited to:

- local/mock demo polish;
- boss walkthrough script;
- dependency audit triage plan;
- monitoring/alerts planning;
- first-pilot readiness checklist;
- docs cleanup;
- owner-question refinement;
- demo evidence organization.

Do not use this list to start deployment, registry, real-provider, billing, SMS, live scraping, or production work.

---

## 6. Boss-facing reminder for William

William, engineering is blocked from starting staging implementation until the required owner/operator values are provided or explicitly deferred.

Please provide the staging basics first:

1. AWS account ID and region — unlocks P4-2 planning for staging config.
2. Runtime config path and KMS/key ownership — unlocks P4-2 config contract.
3. Registry target and push approver — unlocks P4-4 image publishing plan.
4. Staging frontend/API domains plus DNS/TLS owner — unlocks later P4-5 deployment work.
5. Clerk staging values or written approval for limited mock-staging auth — unlocks P4-3 auth work.
6. Migration, deployment, rollback approvers and alert recipients — required before P4-5/P4-6.

Stripe and Resend can wait until after staging basics are locked. They unlock later smoke slices only and do not approve live billing, live email, or cold outreach.

---

## 7. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only the five intended docs are changed/added. |
| Changed-file scope | PASS — no backend, frontend, app config, migration, `.env`, Dockerfile, workflow, package, or test files changed. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Provider SDK/API calls | PASS by scope — docs-only changes; no code or package files changed. |
| Safety boundary | PASS — P4-1b creates a tracker only. No AWS provisioning, deployment, image push, live provider enablement, real billing, production enablement, SMS, or live scraping. |

---

## 8. Final verdict

- P4-1b owner-response tracker created.
- Implementation remains blocked until owner/operator values are LOCKED or explicitly DEFERRED.
- No deployment, AWS provisioning, registry push, live providers, real billing, production enablement, SMS, or live scraping enabled.
