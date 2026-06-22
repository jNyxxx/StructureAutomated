# Phase 0 Readiness Checklist

Date: 2026-06-23
Status: Locally test-gated; live DB smoke deferred

## Verification checklist

| Gate | Status | Evidence |
| --- | --- | --- |
| Backend formatting | Passed | `python -m black --check app tests` |
| Backend lint | Passed | `python -m ruff check app tests` |
| Backend typecheck | Passed | `python -m mypy app tests` |
| Backend tests | Passed | `python -m pytest -q` -> 124 passed |
| Frontend lint | Passed | `npm run lint` |
| Frontend typecheck | Passed | `npm run typecheck` |
| Frontend tests | Passed | `npm run test` -> 14 passed |
| Frontend build | Passed | `npm run build` -> 13 static pages |
| Migration head | Passed | `00010_compliance_suppression` |
| Offline Alembic SQL | Passed | `alembic upgrade head --sql` rendered through head |
| Empty live DB to head | Deferred | No DB URL and Docker unavailable |
| Downgrade/upgrade live smoke | Deferred | No DB URL and Docker unavailable |
| Runtime tenant isolation smoke | Deferred | No DB URL and Docker unavailable |
| Runtime audit append-only smoke | Deferred | No DB URL and Docker unavailable |

## Functional coverage checklist

| Area | Status | Notes |
| --- | --- | --- |
| Tenancy schema + forced RLS | Passed by tests/offline SQL | Runtime DB smoke deferred |
| App-side Clerk mapping/revocation | Passed by tests | Real JWT verifier remains blocker |
| RBAC/object authorization/support access | Passed by tests | Support role is platform/service concept only |
| Mock billing schema/gates | Passed by tests | Real Stripe intentionally deferred |
| Compliance profile/suppression gates | Passed by tests | SMS remains post-MVP |
| Idempotency store | Passed by tests | NULL-safe uniqueness and replay behavior covered |
| Queue/outbox/retry/DLQ | Passed by tests | Worker RLS bypass must remain constrained |
| Audit logging | Passed by tests/offline SQL | Live append-only trigger smoke deferred |
| Credential envelope | Passed by tests | Production KMS/config verification still required |
| Production boot guard | Passed by tests | Must run with production config before launch |
| Frontend auth/tenant/billing/audit wiring | Passed by tests/build | Local/mock Clerk is production-gated |

## Launch blockers

1. Implement or configure real Clerk JWT verification before external users/production.
2. Install/configure real `@clerk/nextjs` runtime before production frontend auth.
3. Replace or back the in-memory rate limiter with Redis/Postgres/shared storage.
4. Run live DB migration, downgrade/upgrade, RLS, tenant isolation, and audit append-only smoke once DB is available.
5. Verify AWS Secrets Manager/KMS configuration before launch.
6. Keep real Stripe out of local MVP; add only when onboarding first paying client.
7. Keep `worker_context` bypass limited to `worker_session`.
8. Keep Slack/internal alerts post-demo unless owner changes scope.

## Completion verdict

Phase 0 is complete for local/demo foundation readiness. It is not cleared for external users or production until the launch blockers and deferred live DB checks are completed.

Phase 1 has not started.
