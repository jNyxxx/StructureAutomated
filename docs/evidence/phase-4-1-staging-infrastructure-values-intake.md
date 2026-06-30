# P4-1 — Staging Infrastructure Values Intake and Lock Packet

**Purpose:** Collect and lock the owner/operator values required before staging config, image publishing, or staging deployment work can begin.
**Slice:** P4-1
**Date:** 2026-06-30
**Status:** Complete — docs-only intake packet. No deployment, AWS provisioning, registry push, real provider enablement, real billing, SMS, or live scraping.
**Base commit:** `1d998ce docs(p4): add staging pilot entry plan`
**Related docs:** [PHASE_4_IMPLEMENTATION_PLAN](../PHASE_4_IMPLEMENTATION_PLAN.md) · [STAGING_ENVIRONMENT_TEMPLATE](../STAGING_ENVIRONMENT_TEMPLATE.md) · [LAUNCH_BLOCKERS_AND_OWNER_DECISIONS](../LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md) · [OPERATIONS_RUNBOOK](../OPERATIONS_RUNBOOK.md)

---

## 1. Current status

| Item | Status |
|---|---|
| Phase 4 planning | OPEN — P4-0 completed and Phase 4 is open for planning only. |
| Staging deployment | BLOCKED — owner/operator values are not locked. |
| AWS account / region | MISSING — no account ID or region has been supplied in the repo docs. |
| Registry target | MISSING — no ECR or alternate registry target has been supplied. |
| Staging domains | MISSING — no approved staging frontend/API domains are locked. |
| Runtime config paths | PROPOSED only — `STAGING_ENVIRONMENT_TEMPLATE.md` recommends `/automatedstructure/staging/...`; no created/approved paths are locked. |
| RDS / Redis sizing | MISSING — no staging service sizes or network placement are locked. |
| Approvers / alert recipients | MISSING — deployment, migration, rollback, alert, and incident owners are not locked. |
| Deployment | NONE — no deployment has occurred. |
| Registry push | NONE — no image push has occurred. |
| Live providers | DISABLED — real sending, cold outreach live sending, Stripe money movement, SMS, and live scraping remain off. |

P4-1 is an intake packet only. It does not grant permission to begin P4-2, P4-4, or P4-5 until the required values are LOCKED or explicitly accepted as deferred by the owner/operator.

---

## 2. Required owner/operator values table

Status meanings:

- **MISSING** — no implementation can start for the blocking slice.
- **PROPOSED** — recommendation only; not permission.
- **LOCKED** — owner/operator supplied and approved.

| Category | Required value | Owner | Current value | Status | Blocking slice | Risk if wrong or skipped |
|---|---|---|---|---|---|---|
| Cloud account | AWS account ID | William / DevOps | Not supplied | MISSING | P4-1, P4-2, P4-4, P4-5 | No staging environment can be targeted; accidental work could occur in the wrong account. |
| Cloud account | AWS region | William / DevOps | Not supplied | MISSING | P4-1, P4-2, P4-5 | Services may be provisioned in the wrong geography or incompatible region. |
| Registry | ECR/registry target | William / DevOps | Not supplied | MISSING | P4-1, P4-4, P4-5 | Images cannot be distributed safely; ad hoc pushes may happen. |
| Platform | ECS/Fargate or approved platform | William / DevOps | ECS/Fargate is recommended in prior planning, but not owner-locked | PROPOSED | P4-1, P4-5 | Deployment work may target the wrong runtime or require rework. |
| Domains | Staging frontend domain | William / DNS/TLS owner | Not supplied | MISSING | P4-1, P4-2, P4-3, P4-5 | Frontend cannot be configured for staging auth, cookies, or CORS. |
| Domains | Staging API domain | William / DNS/TLS owner | Not supplied | MISSING | P4-1, P4-2, P4-3, P4-5 | API base URL, CORS, cookies, and readiness checks cannot be finalized. |
| Domains | DNS/TLS owner | William | Not supplied | MISSING | P4-1, P4-5 | No accountable person for DNS records, certificate validation, or domain incidents. |
| TLS | Certificate/TLS approach | DNS/TLS owner / DevOps | HTTPS required; exact approach not supplied | MISSING | P4-1, P4-5 | Staging may launch without production-like HTTPS/cookie behavior. |
| Runtime config | Secrets Manager base path | DevOps / Security | `/automatedstructure/staging/...` from template only | PROPOSED | P4-1, P4-2, P4-5 | Config may be scattered, hard to audit, or confused with production. |
| Runtime config | KMS key/alias | DevOps / Security | AWS KMS is the approved direction; specific key/alias not supplied | MISSING | P4-1, P4-2, P4-5 | Credential encryption and runtime config resolution cannot be verified. |
| Database | RDS/Postgres engine/version | DevOps / DB owner | PostgreSQL 16-compatible recommended by template | PROPOSED | P4-1, P4-5 | Migration/runtime mismatch or missing required extensions. |
| Database | RDS size/class/storage | DevOps / DB owner | Not supplied | MISSING | P4-1, P4-5 | Under/over-provisioned DB, poor performance, or unnecessary cost. |
| Database | RDS backup retention | DevOps / DB owner | Backups required; exact retention not supplied | MISSING | P4-1, P4-5, P4-10 | No restore assurance; production remains NO-GO. |
| Database | DB role ownership | DevOps / DB owner | Least-privilege app role required; named owner not supplied | MISSING | P4-1, P4-5, P4-6 | App role may be unsafe, superuser-like, or unowned. |
| Redis | Redis/ElastiCache type/size | DevOps / SRE | Managed Redis recommended by template | PROPOSED | P4-1, P4-5, P4-6 | Rate limits may be non-parity or unavailable in staging. |
| Redis | Redis auth/TLS decision | DevOps / SRE | TLS/auth required in principle; exact decision not supplied | MISSING | P4-1, P4-2, P4-5 | Redis URL or traffic may be insecure or incompatible. |
| Release control | Migration approver | William / DevOps | Not supplied | MISSING | P4-1, P4-5 | Schema changes may run without accountability or rollback context. |
| Release control | Deployment approver | William / DevOps | Not supplied | MISSING | P4-1, P4-4, P4-5 | Staging release may happen without approval. |
| Release control | Rollback approver | William / DevOps | Not supplied | MISSING | P4-1, P4-5, P4-6 | Failed staging release may not have a responsible rollback owner. |
| Observability | Alert recipients | William / Ops | Not supplied | MISSING | P4-1, P4-5, P4-9 | Incidents may go unnoticed. |
| Incident response | Incident owner | William / Ops | Not supplied | MISSING | P4-1, P4-5, P4-9 | No accountable person for staging incidents or evidence review. |
| Incident response | Emergency-stop owner | William / Ops | Not supplied | MISSING | P4-1, P4-7, P4-8, P4-9 | No one can halt provider smoke or risky runtime behavior quickly. |
| Observability | Log retention target | William / Ops | Not supplied | MISSING | P4-1, P4-9 | Evidence may be lost too early or retained too long. |
| Observability | Monitoring target | William / Ops | Not supplied | MISSING | P4-1, P4-9 | No target for dashboards, metrics, logs, or alerts. |
| Worker runtime | Worker command/service decision | Engineering / DevOps / William | Worker disabled by default until command is approved | MISSING | P4-1, P4-5, P4-6 | Worker may run wrong command or touch tenant jobs unsafely. |
| Clerk staging | Clerk staging publishable-key owner | William / Auth owner | Not supplied | MISSING | P4-1, P4-3, P4-5 | Frontend cannot complete managed-auth staging smoke. |
| Clerk staging | Clerk staging issuer/JWKS/audience values | William / Auth owner | Not supplied | MISSING | P4-1, P4-3, P4-5 | Backend cannot validate real Clerk staging tokens. |
| Clerk staging | Approved staging auth mode if Clerk values are not ready | William / Security | Mock auth may be allowed only by explicit approval for limited staging demo | MISSING | P4-1, P4-3, P4-5 | Staging auth may be misrepresented as real or bypassed unsafely. |

---

## 3. Proposed safe defaults

These are recommendations only. They are **PROPOSED**, not LOCKED.

| Area | Proposed safe default | Status |
|---|---|---|
| Environment order | Staging first, not production. | PROPOSED |
| Image tags | Commit-SHA image tags for every image. | PROPOSED |
| Image release policy | No latest-only deployment. | PROPOSED |
| Database engine | RDS/Postgres 16-compatible target with required extensions. | PROPOSED |
| Rate-limit backend | Managed Redis/ElastiCache for staging parity. | PROPOSED |
| Runtime config custody | AWS Secrets Manager plus AWS KMS, using `/automatedstructure/staging/...` path convention. | PROPOSED |
| Auth mode | Clerk staging auth preferred; mock auth allowed only with explicit staging-demo approval and clear labeling. | PROPOSED |
| Email | Resend/live email disabled by default. | PROPOSED |
| Billing | Stripe live mode and money movement disabled by default. | PROPOSED |
| Cold outreach | Cold outreach live sending disabled by default. | PROPOSED |
| SMS / scraping | SMS and live scraping disabled by default. | PROPOSED |

---

## 4. Boss-facing checklist for William

Please provide or approve the following before engineering starts staging implementation:

### Infrastructure and domains

- [ ] AWS account ID.
- [ ] AWS region.
- [ ] Registry choice and target: ECR or another approved registry.
- [ ] Deployment platform: ECS/Fargate or another approved platform.
- [ ] Staging frontend domain.
- [ ] Staging API domain.
- [ ] Named DNS/TLS owner.
- [ ] Certificate/TLS approach.

### Runtime config and data services

- [ ] Approve staging runtime config path convention.
- [ ] Provide or approve KMS key/alias owner.
- [ ] Approve RDS/Postgres engine/version.
- [ ] Approve RDS size/class/storage.
- [ ] Approve RDS backup retention.
- [ ] Name DB role owner.
- [ ] Approve Redis/ElastiCache type/size.
- [ ] Approve Redis auth/TLS approach.

### Release and operations

- [ ] Name migration approver.
- [ ] Name deployment approver.
- [ ] Name rollback approver.
- [ ] Provide alert recipients/channel.
- [ ] Name incident owner.
- [ ] Name emergency-stop owner.
- [ ] Approve log retention target.
- [ ] Approve monitoring target.
- [ ] Decide worker command/service strategy for staging.

### Auth mode

- [ ] Provide Clerk staging publishable-key owner.
- [ ] Provide Clerk staging issuer/JWKS/audience values.
- [ ] Decide whether staging should use Clerk first or explicitly approved mock auth first.

---

## 5. Locking rules

- **MISSING** means no implementation can start for the blocking slice.
- **PROPOSED** means recommendation only and does not grant permission.
- **LOCKED** means the owner/operator supplied and approved the value.
- Required values must be LOCKED before P4-2, P4-4, or P4-5 starts, unless a missing value is explicitly accepted as deferred in writing.
- Deferred values must include owner, reason, affected slices, risk, and the next review point.
- Engineering must not invent missing owner values.
- Docs may record recommended defaults, but implementation must wait for LOCKED values.

---

## 6. Hard stop conditions

Stop immediately if any of these happen:

- any real credential appears in docs, repo, logs, prompts, screenshots, or tickets;
- AWS account/region is missing for a staging implementation slice;
- registry target is missing for image publishing;
- staging frontend/API domain is missing for staging deployment;
- rollback approver is missing;
- migration approver is missing;
- alert recipients are missing;
- production environment is accidentally selected;
- live provider flags are enabled;
- Stripe live mode or money movement is enabled;
- cold outreach can reach a live provider;
- boot guard is weakened;
- auth/RBAC/RLS/tenant isolation or billing/send gates are bypassed.

---

## 7. Recommended next slice

| Condition | Next action |
|---|---|
| Values remain MISSING | Send the boss-facing checklist to William and wait. Do not start implementation. |
| Required staging config values are supplied and approved | Start P4-2 staging path and config contract. |
| Registry values are supplied later | P4-4 may be planned after P4-2, but do not jump to deployment. |
| Deployment values are supplied later | P4-5 remains blocked until P4-2/P4-4 prerequisites and approvers are locked. |

Current P4-1 verdict: **P4-2 is BLOCKED** until required values are LOCKED or explicitly deferred.

---

## 8. Verification result

| Check | Result |
|---|---|
| `git diff --check` | PASS — no whitespace errors. Git emitted line-ending warnings only. |
| `git status --short` | PASS — only the five intended docs are changed/added. |
| Changed-file scope | PASS — no backend, frontend, app config, migration, `.env`, Dockerfile, workflow, package, or test files changed. |
| Unsafe-claim grep | PASS — only expected context was found: Phase 4 exit criteria says staging must be deployed later. No claim says production, real sending, or money movement is active. |
| Credential-pattern grep | PASS — no raw live/test key patterns found in changed docs. |
| Registry/deploy command grep | PASS — no registry push or deployment command added. |
| Provider SDK/API calls | PASS by scope — docs-only changes; no code or package files changed. |
| Safety boundary | PASS — P4-1 creates an intake packet only. No AWS provisioning, deployment, image push, live provider enablement, billing money movement, SMS, or live scraping. |

---

## 9. Final verdict

- P4-1 intake packet created.
- Staging values are not locked yet.
- Staging deployment remains blocked.
- No deployment, live providers, real billing, registry push, AWS provisioning, SMS, or live scraping enabled.
