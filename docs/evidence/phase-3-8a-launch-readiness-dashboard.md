# P3-8a — Blocker Consolidation and Launch Readiness Dashboard

**Purpose:** Single consolidated launch readiness reference for Phase 3. Shows what is ready, what is blocked, what the owner must provide, and the recommended next approval.
**Status:** Complete (docs-only).
**Date:** 2026-06-30 (Asia/Manila)
**Base commit:** `27609d3` (P3-6f-prep)
**Audience:** William (owner/boss) + engineering team.

---

## 1. Current demo status

| Check | Status |
|---|---|
| Local/mock browser demo ready | **READY** |
| Demo login (`test@example.com` / `password`) | **PASS** |
| Mock send path (draft → review → send gate → outbound) | **PASS** |
| Backend tests (pytest) | **731 PASS** |
| Frontend tests (vitest) | **141 PASS** |
| Backend production Docker build | **PASS** (`sha256:aa7caf65…`) |
| Frontend production Docker build | **PASS** (`sha256:97bf44c2…`) |
| Local staging rehearsal | **PASS** (base commit `2923f57`) |
| Stripe checkout endpoint | **FAIL-CLOSED** (`503 STRIPE_CHECKOUT_NOT_AVAILABLE`) |
| Stripe portal endpoint | **FAIL-CLOSED** (`503 STRIPE_PORTAL_NOT_AVAILABLE`) |
| Real Resend sending | **DISABLED** |
| Cold outreach live sending | **DISABLED** |
| Registry push | **NONE** |
| Deployment | **NONE** |
| Real secrets | **NONE** |

---

## 2. Completed phase and slice summary

| Slice | Description | Last relevant commit |
|---|---|---|
| **Phase 0** | Multi-tenancy, forced RLS, auth framework, billing states, send gate, agent tools, idempotency, suppression | pre-P3 |
| **Phase 1** | Full backend API (44 paths / 51 ops), 22 migrations, worker stubs | pre-P3 |
| **Phase 2** | Frontend, Phase 2 exit (mock-write layer, live API smoke, 515/122 gates) | pre-P3 |
| **P3-1** | Production-readiness audit — zero true blockers; stop-gates hold | — |
| **P3-1a** | Boot-guard RLS coverage expanded 2 → 29 tables; `controlled_demo` attestation added (fails closed) | — |
| **P3-2** | Live DB smoke — seeded demo; tenant isolation proven under least-privilege role; 44 paths/51 ops all 200 | — |
| **P3-3a–P3-3f** | Clerk readiness: `ClerkJwksVerifier` (RS256/JWKS), managed `AuthService` wiring, `platform_admin` RBAC + migration `00022`, `enforce_mfa()` live, frontend integration designed | — |
| **P3-4** | Rate limits: shared Redis limiter; per-endpoint enforce (auth/import/campaign/send/followup); `RedisRateLimitBackend`; Redis-down → `503 RATE_LIMIT_BACKEND_UNAVAILABLE` | `369df75` |
| **P3-5a–P3-5j** | Resend dual sending: provider Protocol, fail-closed skeleton, webhook foundation, secret-readiness contract, dual-layer scope correction (`send_layer` guard: cold outreach cannot reach Resend; cold outreach = mocked mailbox-pool) | `bb38b13` |
| **P3-6a–P3-6f-prep** | Stripe: owner decision packet, config/readiness contract, owner defaults, webhook verification (HMAC-SHA256, no SDK), checkout/portal skeleton (fail-closed), test-mode smoke prep (values/gates/scenario/evidence defined) | `27609d3` |
| **P3-7a–P3-7e-dryrun** | Deployment: CI validation gates, production Dockerfiles, staging config/secret template, staging release runbook, local staging rehearsal (images boot, migrate, serve, mock login works) | `2923f57` |
| **P3-Demo-1** | Mock send path demo readiness verification | — |
| **P3-Demo-2** | Browser demo login fix: stateful `MockAuthProvider`, credential form (`test@example.com` / `password`), `X-Tenant-ID` seed fix, 14 new tests | `4e7e865` |

---

## 3. Open blocker table

All 38 blockers require owner/operator action. Engineering cannot unblock any of these unilaterally.

| # | Blocker | Owner | Required value / decision | Blocking | Status | Risk if skipped |
|---|---|---|---|---|---|---|
| 1 | William demo review | William | Schedule and attend demo session | P3-Demo sign-off | OPEN | No sign-off recorded |
| **INFRASTRUCTURE / STAGING** | | | | | | |
| 2 | AWS account + region | Owner / DevOps | Account ID + region (e.g. `ap-southeast-1`) | All staging/prod infra | OPEN | No staging environment possible |
| 3 | ECR / registry target | Owner / DevOps | Registry URL for prod image push | P3-7f image push | OPEN | No image distribution |
| 4 | Deployment platform | Owner / DevOps | ECS/Fargate, App Runner, or owner-approved equivalent | P3-7f service deploy | OPEN | No staging deploy |
| 5 | Staging frontend domain | Owner / DevOps | e.g. `app-staging.automatedstructure.com` | P3-7f + Clerk staging | OPEN | No staging frontend |
| 6 | Staging API domain | Owner / DevOps | e.g. `api-staging.automatedstructure.com` | P3-7f + backend staging | OPEN | No staging API |
| 7 | DNS/TLS owner | Owner / DevOps | Named person responsible for DNS + TLS certs | Staging + production | OPEN | No HTTPS, no Clerk |
| 8 | Secrets Manager paths | Owner / DevOps | Confirm `/automatedstructure/staging/…` paths created in AWS | P3-7f secret resolution | OPEN | No secret injection |
| 9 | KMS key alias | Owner / DevOps | KMS key alias or ARN for staging | P3-7f + credential encryption | OPEN | Credential encryption fails |
| 10 | RDS / Postgres staging config | Owner / DevOps | Instance type, VPC, engine version, backup retention | P3-7f DB | OPEN | No persistent DB |
| 11 | Redis / ElastiCache staging config | Owner / DevOps | Instance type, VPC, TLS config | P3-7f rate-limit backend | OPEN | Rate limits non-functional |
| 12 | Backup restore drill | Owner / DevOps | Successful restore test + report | Production launch NO-GO | OPEN | Cannot certify data safety |
| 13 | Production cutover approver | Owner | Named person who signs final go/no-go | Production launch | OPEN | No authority to launch |
| **CLERK / AUTH** | | | | | | |
| 14 | Clerk staging project | Owner | Clerk dev/staging environment + publishable key | P3-3g Clerk wiring | OPEN | No real auth smoke |
| 15 | Clerk staging issuer + JWKS URL | Owner | `AUTH_PROVIDER_ISSUER` + JWKS endpoint | P3-3g token validation | OPEN | `ClerkJwksVerifier` cannot validate |
| 16 | Clerk audience / AZP | Owner | `AUTH_PROVIDER_AUDIENCE`, `AUTH_PROVIDER_AUTHORIZED_PARTIES` | P3-3g token validation | OPEN | Token validation fails |
| 17 | Clerk MFA claim (JWT template) | Owner | `AUTH_PROVIDER_MFA_CLAIM` value in Clerk JWT template | `enforce_mfa()` | OPEN | MFA check cannot verify claim |
| 18 | Clerk staging secret key ref | Owner / DevOps | `/automatedstructure/staging/clerk/SECRET_KEY` | P3-3g backend auth | OPEN | Clerk API calls blocked |
| 19 | Tenant-selector UX after login | Owner | Auto-select first membership OR explicit selector page | P3-3g smoke | OPEN | Post-login `400 TENANT_REQUIRED` |
| **STRIPE** | | | | | | |
| 20 | Stripe smoke approver | Owner | Named person who approves the test-mode smoke window | P3-6h webhook smoke | OPEN | Smoke cannot start |
| 21 | Stripe webhook secret ref | Owner / DevOps | `/automatedstructure/staging/stripe/STRIPE_WEBHOOK_SECRET` (`whsec_…`) | P3-6g secret wiring | OPEN | Webhook route stays fail-closed |
| 22 | Stripe test secret key ref | Owner / DevOps | `/automatedstructure/staging/stripe/STRIPE_SECRET_KEY` (`sk_test_…`) | P3-6g secret wiring | OPEN | Cannot verify test keys |
| 23 | Stripe test price IDs | Owner | Plan → Stripe price ID mapping for test mode | P3-6k checkout activation | OPEN | Checkout sessions blocked |
| 24 | Stripe billing owners | Owner | Named billing-state owner + billing-portal owner | P3-6i mutation design | OPEN | No billing escalation path |
| **RESEND (TRANSACTIONAL)** | | | | | | |
| 25 | Resend API secret ref | Owner / DevOps | `/automatedstructure/staging/email/RESEND_API_KEY` (non-placeholder) | P3-5h transactional smoke | OPEN | Resend cannot send |
| 26 | Resend webhook secret ref | Owner / DevOps | `/automatedstructure/staging/email/RESEND_WEBHOOK_SECRET` | P3-5h webhook verify | OPEN | Webhook route stays fail-closed |
| 27 | Resend DNS verification | Owner / DevOps | SPF/DKIM/DMARC verified for `outreach.automatedstructure.com` | P3-5h smoke + live send | OPEN | Deliverability blocked |
| 28 | Resend internal smoke approval | Owner | Named approver + smoke window for one internal test email | P3-5h transactional smoke | OPEN | Cannot run internal smoke |
| 29 | Resend legal footer details | Counsel / Owner | Company name, physical address, unsubscribe URL | All outbound sends | OPEN | Legal compliance gap |
| 30 | Monitored Reply-To address | Owner | `replies@automatedstructure.com` inbox confirmed monitored | Resend smoke + live send | OPEN | Replies go unread |
| 31 | Emergency-stop owner | Owner | Named person who can revoke API key or halt sending instantly | Resend + Stripe smokes | OPEN | No incident escalation |
| 32 | Deliverability-monitor owner | Owner | Named person monitoring bounce/complaint rates | Live sending | OPEN | Bounce/complaint spikes undetected |
| 33 | Counsel-approved outreach/privacy language | Counsel | Legal sign-off on outreach copy, privacy policy, unsubscribe/data-use | Live sending | OPEN | Legal launch blocker |
| **COLD OUTREACH** | | | | | | |
| 34 | Cold outreach mailbox-pool plan | Owner | Decision on when/how to build live mailbox-pool manager | Post-MVP cold outreach | OPEN | Cold outreach stays mocked |
| 35 | `LIVE_COLD_SENDING_ENABLED` kill switch | Owner | Explicit approval before cold outreach layer goes live | Mailbox-pool activation | OPEN | Hard blocker — cannot enable |
| **LEGAL / COMPLIANCE / OTHER** | | | | | | |
| 36 | Legal/compliance approval | Counsel | Full legal review of privacy, outreach, retention, jurisdictions | External users + live send | OPEN | Legal launch blocker |
| 37 | SMS provider + legal wording | Owner / Counsel | SMS provider choice + A2P 10DLC + counsel-approved copy | SMS features | OPEN (deferred) | SMS blocked |
| 38 | CRE research source approval | Owner / Legal | Approval to use live scraping / paid research | Live enrichment | OPEN (deferred) | Research stays mock |

---

## 4. Readiness categories

| Category | Status | Primary blockers |
|---|---|---|
| **Demo readiness (local/mock)** | **READY** | None. William can review the demo now. |
| **Staging deployment readiness** | **BLOCKED** | #2–13 (AWS, domains, TLS, Secrets Manager, RDS, Redis, backup, cutover approver) |
| **Clerk production auth readiness** | **BLOCKED** | #14–19 (Clerk staging project + all values + tenant-selector UX) |
| **Transactional Resend readiness** | **BLOCKED** | #25–33 (secret refs, DNS, smoke approval, legal footer, Reply-To, emergency-stop, deliverability owners, counsel sign-off) |
| **Cold outreach live readiness** | **BLOCKED** | #34–35 (mailbox-pool not designed; `LIVE_COLD_SENDING_ENABLED` kill switch approval required) |
| **Stripe test-mode readiness** | **BLOCKED** | #20–22 (smoke approver + webhook secret ref + test key ref) |
| **Stripe live-money readiness** | **BLOCKED** | All Stripe test-mode blockers + separate live-mode owner approval + distinct live key refs |
| **Production launch readiness** | **BLOCKED** | All of the above + #12, #13, #29–30, #33, #36 (backup drill, cutover approver, legal/compliance, counsel) |

---

## 5. Recommended next paths

| If William provides… | Recommended next slice | Engineering ETA |
|---|---|---|
| Only wants the local demo | Show demo now. No further engineering action needed. | Immediate |
| AWS account/region + domains + Secrets Manager paths | **P3-7f** — staging deployment (ECS/Fargate + RDS + Redis + image push + smoke) | After values received |
| Clerk staging publishable key + issuer + JWT values | **P3-3g** — Clerk frontend integration (`clerk-real.tsx`, `@clerk/nextjs`, catch-all routes, tenant-selector) | After values received |
| Stripe smoke approver + webhook secret ref + test key ref | **P3-6g** secret wiring → **P3-6h** internal webhook smoke | After values received |
| Resend refs + DNS verification + legal footer + smoke approval | **P3-5h** — real transactional internal smoke (one internal email only) | After values received |
| Nothing above by a deadline | **Phase 3 final handoff package** — freeze engineering scope; deliver everything as ready-for-owner-action | Immediate |

Engineering cannot unblock items #2–38 unilaterally. All require owner/operator decisions
or external actions (DNS, AWS, legal review, Clerk dashboard, Stripe dashboard).

---

## 6. Risk notes

1. **Do not confuse Resend transactional sending with cold outreach.** Resend is for system
   notifications and opted-in drips only. Cold outreach (prospecting emails) routes to the
   future mailbox-pool layer. The `send_layer` guard in `sending.py` enforces this in code —
   cold outreach intent cannot reach the Resend adapter.

2. **Do not run cold outreach through Resend.** `LIVE_COLD_SENDING_ENABLED` is a hard kill
   switch. Cold outreach cannot go live without explicit owner approval recorded in
   `LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`.

3. **Do not enable Stripe live money.** Test-mode smoke (P3-6h) must complete and produce
   evidence first. Live-mode approval is a separate owner decision requiring distinct live
   API key refs and a production deployment approval.

4. **Do not deploy before staging prerequisites are complete.** The staging runbook defines
   20 prerequisites — all open. Real staging deploy is blocked until AWS, domains, TLS,
   Secrets Manager, RDS, Redis, Clerk values, and migration approval are confirmed.

5. **Do not use production mock-provider exceptions without explicit attestation.**
   `controlled_demo` requires a named `CONTROLLED_DEMO_APPROVED_BY` value. Boot guard fails
   closed in production if this is not recorded.

6. **Do not bypass central billing gates.** `is_active(tenant)` and `has_feature(tenant, key)`
   are the authoritative gates. Scattered billing `if` checks in routes, services, or workers
   violate the CLAUDE.md non-negotiable engineering rules.

7. **Do not create test infrastructure that could be mistaken for production.** All staging
   images use `APP_ENV=staging`, not `production`. Production requires full boot-guard pass
   including secrets, Redis, RLS role checks, Clerk, KMS, and migration alignment.

---

## 7. Boss-facing summary (for William)

**AutomatedStructure — Phase 3 Launch Readiness**
**Date:** 2026-06-30

---

### What is ready

The local/mock demo is fully functional:

- Browser sign-in works (`test@example.com` / `password`).
- The full mock send path runs end-to-end: contact selection → AI draft → human review → send gate → mock outbound record → audit trail.
- Backend: 731 automated tests pass. Frontend: 141 tests pass.
- Production Docker images build and boot cleanly. A local rehearsal confirmed the images serve health checks, run migrations, and allow mock login.

All safety gates are verified and fail-closed:

- Stripe: no sessions, no charges, no live keys — all endpoints return `503` until you provide test credentials.
- Resend: adapter built but disabled — no email has been sent, no credentials exist.
- Cold outreach: mocked — cannot reach any live sending provider; a code guard enforces this.
- Production: not deployed, no registry push, no AWS provisioned.

---

### What is blocked and why

All remaining Phase 3 tracks require values that only you can provide. Engineering
has built all the code foundations and documented the exact inputs needed. Nothing
can proceed on staging, real email, Stripe test mode, or production until these are
supplied.

---

### What you need to provide

Choose based on priority:

**To show the demo right now:**
Nothing. It is ready.

**To move toward a real staging environment:**
- AWS account ID + region
- Deployment platform choice (ECS/Fargate recommended)
- Staging frontend domain + staging API domain
- Named DNS/TLS owner
- Confirmation that Secrets Manager / KMS is set up

**To enable real transactional email (system notifications, account confirmations):**
- Resend API key — stored via AWS Secrets Manager, not committed
- DNS verification for `outreach.automatedstructure.com` (SPF/DKIM/DMARC)
- Counsel-approved legal footer: company name, physical address, unsubscribe URL
- Named emergency-stop operator (can kill API key if incident)
- Named deliverability monitor (watches bounce/complaint rates)
- Your approval for one internal test email before any external send

**To run Stripe test-mode webhooks:**
- Stripe test webhook signing secret — stored via Secrets Manager
- Stripe test API key — stored via Secrets Manager
- Your name as the smoke approver

**To wire real Clerk authentication:**
- Clerk staging publishable key + issuer URL
- Clerk JWT template with MFA claim
- Decision: auto-select first tenant after login, or show a tenant picker page

---

### Recommended next approval

**If you want to show the demo:** no action needed from you — it is ready now.

**If you want to move toward a real environment:** the highest-leverage next step
is providing the AWS account details and staging domain names. This unlocks the
staging deployment track (P3-7f). Clerk, Stripe, and Resend tracks can follow
in any order once those values are provided.

**If you want to close Phase 3 without a real environment:** say the word and
engineering will produce a final Phase 3 handoff package and freeze scope
until you are ready to provide the owner values.

---

## 8. Files created / updated

Created:

- `docs/evidence/phase-3-8a-launch-readiness-dashboard.md`

Updated:

- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/DOCUMENTATION_MANIFEST.md`

---

## 9. Final verdict

P3-8a complete. Launch readiness dashboard created. 38 open blockers documented with owners, required values, blocking slices, and risks. Readiness categories confirmed (demo READY; all real-provider/staging/production tracks BLOCKED). Recommended next paths enumerated per William's priority choice. Boss-facing summary written for direct delivery.

No live providers, no deployment, no real secrets, no registry push enabled.
