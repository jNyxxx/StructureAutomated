# Phase 3 Demo-1: Phase 0 + Mock Send Path Readiness

**Date:** 2026-06-29
**Status:** Complete for local/mock demo-readiness evidence

> **Correction added 2026-06-30 (P3-Demo-2):** This evidence file claimed the browser demo was ready. Manual browser testing after P3-Demo-1 found the sign-in page showed a dead Clerk shell with no way to log in without real Clerk credentials. P3-Demo-2 fixed this by adding a stateful `MockAuthProvider` with a "Continue with Demo Account" button (local/mock mode only), seeding `X-Tenant-ID` from `auth.tenantId` to fix the 400 on `/auth/me`, and adding tests. See [phase-3-demo-2-local-mock-auth-readiness.md](phase-3-demo-2-local-mock-auth-readiness.md).
**Scope:** Evidence/readiness only — Phase 0 secure foundation + local/mock cold-outreach send path
**Production status:** NOT enabled
**Provider status:** Real Resend sending disabled; real Stripe billing disabled; cold outreach actual send mocked

---

## 1. Purpose

Boss instruction: ping when Phase 0 + the mock send path are demoable.

This document verifies that the local/mock MVP demo can show the secure foundation, tenant/auth/billing/access gates, human review, send gate, rate limits, mock-provider send intent creation, outbound message records, audit behavior, and mock dashboard read paths without enabling real providers, production deployment, Stripe money movement, SMS, or live scraping.

---

## 2. Preflight

Commands run from `D:\AutomatedStructure`:

```text
git fetch origin
git status --short
git log --oneline -15
git ls-remote origin refs/heads/master
git rev-parse HEAD
git rev-parse origin/master
find .git -name '*.lock' -print
ps -ef | grep -Ei 'pytest|ruff|black|mypy|npm|node|vite|next|docker|codex|claude|python' | grep -v grep || true
```

Result:

```text
HEAD = bb38b13b47d311965a04065af2b07ce1e6b2b8ea
origin/master = bb38b13b47d311965a04065af2b07ce1e6b2b8ea
latest commits include:
bb38b13 docs(p3-5j): lock dual sending layer scope
f64c1ca feat(p3-5j): add send_layer guard — cold outreach cannot reach Resend
0d13e1a feat(p3-6): add Stripe checkout portal skeleton
65450a3 feat(p3-6): add Stripe webhook verification foundation
b82864a ci(p3-7): add validation gates without deployment

.git lock files: none found
concurrent writer/agent/test process: none found
```

Preflight note: initial `git status --short` showed one zero-byte untracked local artifact named `nul`. It was inspected (`0 bytes`) and removed before documentation work. `git status --short` was clean before creating this evidence file.

---

## 3. Files inspected

Evidence / docs:

- `docs/evidence/phase-0-final-verification.md`
- `docs/evidence/phase-0-readiness-checklist.md`
- `docs/evidence/phase-1-final-verification.md`
- `docs/evidence/phase-1-readiness-checklist.md`
- `docs/evidence/phase-2-exit-completion.md`
- `docs/evidence/phase-3-5j-dual-sending-layer-scope-correction.md`
- `docs/EMAIL_COMPLIANCE_AND_SEND_GATE.md`
- `docs/API_CONTRACT.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`
- `docs/PHASE_3_IMPLEMENTATION_PLAN.md`

Backend:

- `backend/app/routers/sending.py`
- `backend/app/services/mock_sender.py`
- `backend/app/services/email_provider.py`
- `backend/app/services/send_gate.py`
- `backend/app/services/stripe_billing.py`
- campaign, draft, review, deliverability, outcome, billing, compliance, rate-limit services/repositories by file discovery and prior evidence links

Frontend:

- Route coverage discovered for dashboard, campaigns, campaign drafts, review queue, billing, deliverability, outcomes, prospects/import, compliance/suppression/settings, audit logs.
- Frontend tests confirm backend mock API wiring for campaign update, draft errors, review approve/reject/regenerate, send-gate dry-run, mock send intent, follow-up rule/schedule/mock-run, compliance update, suppression create, and strict backend error handling.

---

## 4. Demo flow checklist

| Demo item | Result | Evidence |
|---|---:|---|
| Tenant-aware login/auth mock or current safe auth path | PASS | Phase 2 exit records local mock auth attached only outside production and auth-gated `/auth/me` smoke. P3-3 managed auth work remains production-gated. |
| Tenant/RBAC/object authorization/RLS foundation | PASS | Phase 0 evidence records forced RLS, tenant helper, RBAC/object auth, support access, audit, and boot-guard coverage; P3-1a expanded boot-guard RLS table coverage. |
| Billing/access gates | PASS | Central `BillingGateService` remains in send gate; Stripe is disabled/fail-closed; mock billing remains default. |
| Campaign creation/select contacts | PASS | Phase 1/2 evidence and frontend tests cover campaign create/update/contact select through backend mock APIs. |
| AI draft/mock draft generation | PASS | Phase 1 evidence covers structured mock draft generation; frontend routes/tests cover draft generation errors and read path. |
| Evidence/grounding display | PASS | Phase 1 evidence covers RAG grounding, groundedness/citation validation, and frontend draft/evidence display path. |
| Human review approval | PASS | `SendGateService` requires an approved review item before send; frontend tests cover approve/reject/regenerate actions. |
| Send gate dry-run | PASS | `/api/v1/send-gate/dry-run` route enforces auth, idempotency, rate limit, and gate evaluation; it never sends. |
| Mock send intent creation | PASS | `/api/v1/send-intents` uses `MockSenderService` and returns production-shaped mock result after gates pass. |
| Outbound message record | PASS | `MockSenderService` creates `outbound_messages` with `status="mock_sent"` on success and `status="blocked"` on gate/provider failure. |
| Audit trail | PASS | Send gate and mock sender emit `send_gate.passed/failed`, `outbound_message.sent`, `outbound_message.blocked`, and provider failure audit events. |
| Deliverability/outcomes dashboard mock/read path | PASS | Phase 1 evidence covers deliverability/outcomes services; frontend build includes `/deliverability` and `/outcomes` routes and tests pass. |
| Suppression/compliance gate behavior | PASS | `SendGateService` checks `ComplianceGateService.is_suppressed()` before send; Phase 1 negative tests cover suppressed contact blocks. |
| Rate-limit behavior | PASS | `sending.py` applies `enforce_send_gate_rate_limit` and `enforce_send_intent_rate_limit`; P3-4f accepts rate-limit/Redis hardening as green. |

Verdict: the local/mock demo path is demoable without enabling real sending, real billing, production, SMS, or live scraping.

---

## 5. Cold outreach mock-send safety

| Check | Result |
|---|---:|
| Cold outreach request shape uses `send_layer="cold_outreach"` default | PASS |
| Missing/ambiguous `send_layer` fails closed for Resend | PASS — default is `cold_outreach`, and Resend rejects it |
| Cold outreach cannot resolve to Resend delivery | PASS — `ResendEmailSendProvider.send()` raises `COLD_OUTREACH_NOT_ALLOWED` before live-send checks |
| Cold outreach sends are mock-only for MVP | PASS — send-intent route builds `MockSenderService`; default provider config is `EMAIL_PROVIDER=mock` |
| Future mailbox-pool manager remains separate | PASS — documented in P3-5j and send gate docs as future layer |
| Live cold domains configured/acquired | PASS as safety check — none configured/acquired |
| `LIVE_COLD_SENDING_ENABLED` exists | NOT YET — correctly recorded as a future hard blocker before mailbox-pool live phase |

Cold outreach MVP behavior remains: real send disabled, mailbox-pool live implementation deferred, no Resend cold outreach path.

---

## 6. Transactional Resend safety

| Check | Result |
|---|---:|
| Resend scope is transactional/opted-in only | PASS — P3-5j records autoresponders, opted-in drip, and system-notification scope only |
| Resend remains disabled/fail-closed | PASS — skeleton raises `LIVE_EMAIL_PROVIDER_DISABLED` for transactional sends |
| No Resend SDK/API call exists | PASS — grep found no `import resend`, `from resend`, `api.resend`, or `resend.com` in app/frontend/workflow code |
| No real credentials added | PASS — only secret-ref placeholders/config fields exist; no raw values added |
| DNS configured | PASS as safety check — no DNS configured by repo work |
| Open/click tracking enabled | PASS as safety check — not enabled; webhook foundation ignores open/click tracking |
| Cold outreach reaches Resend | PASS as safety check — blocked with `COLD_OUTREACH_NOT_ALLOWED` |

Command used for SDK/API scan:

```text
grep -Ei '(^|[[:space:]])(resend|stripe)([=<>~ ]|$)' backend/requirements.txt frontend/package.json frontend/package-lock.json 2>/dev/null || true
git grep -n "import resend\|from resend\|api.resend\|resend.com\|import stripe\|from stripe\|api.stripe\|stripe.com" -- backend/app frontend/app frontend/components frontend/lib .github || true
```

Result only matched internal app module import `from app.services.stripe_billing import stripe_billing_config_failures`; no Resend SDK/API import/call was present.

---

## 7. Stripe safety

| Check | Result |
|---|---:|
| Mock billing remains default | PASS — `mock_stripe=True`; checkout and portal flags default false |
| Checkout/portal skeleton fails closed | PASS — disabled provider raises `STRIPE_CHECKOUT_NOT_AVAILABLE`, `STRIPE_PORTAL_NOT_AVAILABLE`, or `STRIPE_BILLING_DISABLED` |
| No Stripe SDK/API call exists | PASS — no `import stripe`, `from stripe`, `api.stripe`, or `stripe.com` in app/frontend/workflow code |
| Real checkout session | PASS as safety check — not implemented |
| Real billing portal session | PASS as safety check — not implemented |
| Money movement | PASS as safety check — not implemented/enabled |
| Tenant billing-state mutation from Stripe | PASS as safety check — webhook foundation normalizes safe events only; no tenant mutation |

---

## 8. Production safety

| Check | Result |
|---|---:|
| Production enabled | PASS as safety check — NOT enabled |
| Deployment workflow/job | PASS as safety check — no deploy/release job added |
| Registry push | PASS as safety check — no registry push; CI Docker job is validation-only/no push |
| AWS provisioning | PASS as safety check — none performed |
| Boot guard intact | PASS — production/staging safety guards remain documented and tested |
| CI validation gates intact | PASS — P3-7d-impl validation gates remain in `.github/workflows/ci.yml`; no release behavior added |
| Real `.env` files changed | PASS — no tracked or real `.env` changed |
| SMS/live scraping | PASS as safety check — still disabled/deferred |

Workflow scan result:

```text
.github/workflows/ci.yml contains Docker build validation only; grep found no docker push, registry push, AWS deployment, staging release, or production release job.
```

---

## 9. Backend gate results

Run from `backend/`:

| Command | Result |
|---|---:|
| `python -m ruff check app tests` | PASS — all checks passed |
| `python -m black --check app tests` | PASS — 214 files unchanged |
| `python -m mypy app --ignore-missing-imports` | PASS — no issues in 156 source files |
| `python -m pytest -q --tb=short --disable-warnings` | PASS — quiet progress reached 100% and command exited 0 |
| `python -m pytest tests/test_resend_email_provider.py tests/test_router_billing.py -q` | PASS — targeted Resend/Stripe safety tests passed |

---

## 10. Frontend gate results

Run from `frontend/`:

| Command | Result |
|---|---:|
| `npm ci` | PASS — install completed; npm audit reports 10 dependency vulnerabilities (4 moderate, 5 high, 1 critical). No auto-fix run. |
| `npm run lint` | PASS — no ESLint warnings/errors |
| `npm run --silent typecheck` | PASS — no output, exit 0 |
| `npm run test` | PASS — 3 files / 122 tests passed |
| `npm run build` | PASS — Next.js production build compiled successfully; 27 static pages generated |

Frontend test notes: expected local/mock fallback warnings appeared for unavailable backend calls. Tests assert these paths do not claim success when backend/network errors occur.

---

## 11. Docker build results

| Command | Result |
|---|---:|
| `docker build -f backend/Dockerfile.prod -t automatedstructure-backend:p3-demo-1-local backend` | PASS — image built as `automatedstructure-backend:p3-demo-1-local` |
| `docker build -f frontend/Dockerfile.prod -t automatedstructure-frontend:p3-demo-1-local frontend` | PASS — image built as `automatedstructure-frontend:p3-demo-1-local` |

Docker Desktop was rechecked after the daemon came online:

```text
Docker client: 29.5.3
Docker server: Docker Desktop 4.78.0 / Engine 29.5.3
Context: desktop-linux
```

Both production Docker builds completed successfully. No registry push or deployment was attempted.

---

## 12. Safety grep / changed-file checks

| Check | Result |
|---|---:|
| `git diff --check` | PASS — no whitespace errors; Git emitted line-ending normalization warnings only |
| Changed files checked for accidental live-send / production / money claims | PASS — matches are deny/disabled/not-enabled statements only |
| Changed files checked for secret-looking values | PASS — no raw secrets added |
| Real `.env` files changed | PASS — none |
| Resend SDK/API call added | PASS as safety check — none |
| Stripe SDK/API call added | PASS as safety check — none |
| Registry push/deployment workflow added | PASS as safety check — none |

---

## 13. Owner ping draft — do not send automatically

> Phase 0 + the local/mock send path are demoable.
>
> The demo can show the secure foundation, tenant/auth/RBAC/RLS controls, centralized mock billing/access gates, campaign/contact flow, mock draft generation with grounding/evidence, human approval, send-gate dry-run, mock send-intent creation, outbound message record, audit trail, suppression/compliance gates, rate limits, and mock deliverability/outcomes dashboards.
>
> Important safety note: no real Resend sending, no Stripe checkout/money movement, no DNS configuration, no production deployment, no AWS provisioning, no SMS, and no live scraping were enabled. Cold outreach remains mock-only for MVP and cannot route through Resend. Resend is now reserved for future transactional/opted-in sending only, behind separate approval and readiness gates.
>
> Remaining blockers before anything live: first paying client approval, real Resend transactional secrets/DNS/legal approval, cold mailbox-pool live domain plan + kill switch, Stripe test/live billing approvals, AWS/staging deployment values, Clerk frontend cutover values, legal/compliance copy, and staging smoke evidence.

---

## 14. Remaining live blockers

- First paying client approval.
- Real Resend transactional secret refs/resolution, DNS proof, monitored Reply-To, legal footer/counsel approval, and explicit internal-smoke approval.
- Cold outreach mailbox-pool live domain/subdomain plan, warm-up plan, `LIVE_COLD_SENDING_ENABLED` kill switch, and separate owner approval.
- Stripe test/live billing approvals, real session creation approval, billing-state mutation design, price IDs/refs, named billing owners, and money-movement approval.
- AWS/staging deployment values: account/region, deployment target, registry, RDS, Redis/ElastiCache, Secrets Manager/KMS, domains/TLS, backups/RPO/RTO, alerts, migration/rollback owners, cutover approver.
- Clerk frontend integration values and real-JWT smoke.
- Legal/privacy/unsubscribe/outreach language sign-off.
- Production mock-provider exception remains default-denied unless explicitly approved.

---

## 15. Final verdict

- **P3-Demo-1 evidence/readiness slice:** complete.
- **Mock send path:** demoable in local/mock mode.
- **Real providers:** no real Resend, Stripe, SMS, live scraping, AWS, registry push, or production deployment enabled.
- **Docker replay:** backend and frontend production Docker builds passed locally with `p3-demo-1-local` tags after Docker Desktop Linux engine came online.
