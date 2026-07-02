# P4-LocalE2E-SmokeScript

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `b7effa4 chore(p4): add local fresh-volume bootstrap`
**Status:** COMPLETE. A single repeatable command now exercises the full local/mock happy path over real HTTP against the running Docker stack, verified to pass 5 consecutive times against the normal long-lived dev volume with no state growth.

## Scope

Local-only. Adds one new backend script and its tests, fixes one identity-provider drift bug in `bootstrap_local_demo.py` (with a new regression test) that the smoke script's first live Docker run uncovered, and rewrites the smoke script's idempotency-replay handling after real Docker runs proved the original assumption wrong. No staging/production/live-provider changes, no `p4/next15-upgrade` merge, no package/dependency changes, no real `.env` changes, no Docker image/compose structural changes.

## What this closes

`docker compose exec backend python -m app.scripts.local_e2e_smoke` is now the single repeatable local Docker E2E smoke command: bootstrap → seed → login → contact import → contact readback → campaign create → contact selection → draft generation → evidence read → review queue → approve → send-gate dry run → mock send → outbound readback → audit trail → logout/re-login. It refuses to run outside `local`/`development`/`demo` and prints `[PASS] step: detail` per step, `SMOKE PASSED (N/N)` or `SMOKE FAILED at <step>`.

## Bugs found and fixed while exercising the path for the first time

Both bugs were invisible to unit tests and to the previous fresh-*empty*-volume verification (`docs/evidence/phase-4-fresh-volume-bootstrap.md`) — they only surface when the same idempotent script is run more than once against a volume that already has state, which is exactly what "repeatable" requires proving.

### 1. `bootstrap_local_demo.py` used the wrong `identity_provider`, breaking its own idempotency check

`app/scripts/bootstrap_local_demo.py` provisioned the demo `users` row with `identity_provider="local_mock"`. The real auth path (`app/auth/local_mock._LocalMockUsers`, an in-memory mock that never touches the `users` table) always mints principals with `identity_provider="clerk"` — matching the real Clerk-backed schema convention. The long-lived dev volume's `users` row (created manually during P3-2, `docs/evidence/phase-3-2-live-db-smoke.md`) already had `identity_provider='clerk'`.

Effect: `bootstrap_local_demo`'s own idempotency check (`user_repo.get_by_identity(identity_provider="local_mock", ...)`) never found the existing row, so every re-run attempted to `INSERT` a user with an id that already existed, crashing with `IntegrityError: duplicate key value violates unique constraint "users_pkey"`. This did not affect authentication itself (the mock auth path never reads the real row), but it broke bootstrap's idempotency on any volume carrying the older manually-seeded row — including the normal dev stack every contributor actually runs against.

Fix: changed `_USER_IDENTITY_PROVIDER` to `"clerk"` in `bootstrap_local_demo.py`. Updated `test_bootstrap_local_demo.py`'s partial-state test (which had baked in the same wrong value) and added `test_bootstrap_user_identity_matches_local_mock_auth_users`, which asserts the constant round-trips through `_LocalMockUsers.get_by_identity` — this pins the two independent identity conventions together so they cannot drift apart silently again.

### 2. Idempotent replay responses return a null resource everywhere — the smoke script assumed otherwise

`local_e2e_smoke.py`'s original docstring claimed "later runs replay the same cached responses." Running it a second time against Docker crashed immediately at `contact_import` with `TypeError: 'NoneType' object is not subscriptable`.

Root cause (by design, not a bug in the app): `app/services/idempotency.py` only persists a request/response **hash**, never the payload (rule 14 in spirit — least data retention). Every idempotency-gated service (`csv_import.py`, `campaign.py` ×3, `review.py`, `send_gate.py`, `mock_sender.py`) follows the same pattern: on `IdempotencyState.REPLAY` it returns `{resource: None, idempotency_replay: true}`. This is consistent and deliberate across the whole codebase — confirmed by reading all six call sites — so the smoke script's assumption that a replay returns usable resource data was simply wrong.

Fix: rewrote every gated step in `local_e2e_smoke.py` to check `idempotency_replay` and recover state through a GET/list lookup instead of trusting the POST body:

| Step | Replay recovery |
|---|---|
| contact_import | No lookup endpoint exists. `import_id` stays `None`; excluded from the audit-trail's required-object set, and `contact_import.completed` is dropped from the expected event types only when `import_id` is unknown. |
| campaign_create | `GET /api/v1/campaigns`, matched by the deterministic campaign name. |
| campaign_contact_select | No lookup endpoint exists. Replay trusted at face value (envelope-shape checked only). |
| draft_generate | `GET /api/v1/review/items?campaign_id=...` to recover `draft_id` (every review item carries it regardless of the draft's own replay state), then `GET /api/v1/drafts/{id}` to re-verify `status == "generated"`. |
| review_approve | `GET /api/v1/review/items/{review_id}` to re-verify `status == "approved"`. |
| send_gate_dry_run | No lookup endpoint for the stored gate result exists. `mock_only` stays independently verifiable (defaults `True` on both fresh and replayed results in `send_gate.py`); `status == "passed"` is trusted at face value on replay. |
| mock_send | No lookup by id; deferred to the outbound-readback step. |
| outbound_readback | Matched by `draft_id` instead of by the send response's `outbound_message_id` — works identically whether `mock_send` was new or replayed, and is now the source of `state.outbound_message_id` for the audit-trail check. |

Also extended `_find_in_pages` with an `extra_params` option (needed to pass `campaign_id` through to the review-items lookup) and updated the module docstring to describe the real contract instead of the disproven assumption.

## Tests added/updated

`backend/tests/test_local_e2e_smoke.py` (7 tests, up from 6):

- 4 pre-existing tests unchanged in intent (env guard ×2, `needs_regeneration` failure, non-mock-send failure, no-secrets-in-output) — all now exercise the rewritten step logic on the non-replay path.
- `_build_handler` gained a `replay: bool` parameter that flips every idempotency-gated endpoint to the real `{resource: None, idempotency_replay: true}` shape, plus new lookup-endpoint branches (`GET /api/v1/campaigns`, `GET /api/v1/drafts/{id}`, `GET /api/v1/review/items/{id}`) and a `draft_id` field on the outbound-messages list item (now required by the readback step regardless of replay).
- New: `test_smoke_happy_path_handles_idempotent_replay_at_every_step` — runs the full 16-step flow entirely through the replay branch and asserts all state (`campaign_id`, `draft_id`, `review_id`, `outbound_message_id`) is correctly recovered via lookups, `import_id` is correctly left `None`, and the replay note appears in stdout.

`backend/tests/test_bootstrap_local_demo.py` (7 tests, up from 6):

- `test_bootstrap_partial_state_is_completed_not_duplicated`'s fake existing user now uses `identity_provider="clerk"` (matching the fix) instead of the old wrong value.
- New: `test_bootstrap_user_identity_matches_local_mock_auth_users` — asserts `bootstrap_local_demo`'s identity constants resolve through the real `_LocalMockUsers.get_by_identity`, pinning the two conventions together.

## Gate results

Backend gates:

| Gate | Result |
|---|---|
| `python -m ruff check app tests` | PASS |
| `python -m black --check app tests` | PASS — 223 files unchanged |
| `python -m mypy app --ignore-missing-imports` | PASS — 160 source files |
| `python -m pytest -q` | PASS — 816 tests |

Frontend gates (no frontend files changed; run for completeness):

| Gate | Result |
|---|---|
| `npm run lint` | PASS — no ESLint warnings/errors |
| `npm run typecheck` | PASS |
| `npm run test -- --run` | PASS — 142 tests |
| `npm run build` | PASS — 27 routes |

Docker verification against the normal, long-lived dev stack (`automatedstructure_db_data` — not an isolated fresh volume; this volume carries real accumulated state from prior P3/P4 work, which is precisely what exposed both bugs above):

| Step | Result |
|---|---|
| Docker Desktop/WSL2 environment recovery (see note below) | PASS after clean restart |
| `docker compose up -d --build` | PASS — all 5 containers up |
| `docker compose exec backend alembic upgrade head` | PASS — `00022_platform_admin_role` (head) |
| `GET /health`, `/live`, `/ready` | PASS |
| `docker compose exec backend python -m app.scripts.bootstrap_local_demo` (1st call, post-fix) | PASS — `user: SKIPPED (already_exists)` (previously crashed with `IntegrityError`) |
| `docker compose exec backend python -m app.scripts.bootstrap_local_demo` (2nd call) | PASS — all 5 entities `SKIPPED (already_exists)` |
| `docker compose exec backend python -m app.scripts.seed_local_grounding` | PASS — `SKIPPED (already_seeded)` |
| `docker compose exec backend python -m app.scripts.local_e2e_smoke` | PASS — `SMOKE PASSED (16/16)` |
| Repeated 4 more times back-to-back | PASS — `SMOKE PASSED (16/16)` every time, identical `campaign_id`/`draft_id`/`review_id`/`outbound_message_id` recovered via replay lookups on every run after the first |

### Local environment note (not a code issue)

Docker Desktop was found in a broken state at the start of this work (500 Internal Server Error on the named pipe, orphaned `com.docker.backend`/`com.docker.build` processes surviving a restart). Root cause was unrelated to this repo: the host `C:` drive had only 0.2 GB free, so Docker's WSL2 virtual disk could not grow and every write (including `containerd`'s metadata store) failed with `input/output error`. The user freed space on `C:` (0.2 GB → 7.5 GB); a subsequent clean Docker Desktop restart resolved it fully with zero data loss to the existing `automatedstructure_db_data`/`automatedstructure_n8n_data` volumes. Recorded here only because it's why this evidence doc has an unusually detailed Docker-recovery trail — no code or config change was made to address it.

## Safety confirmation

- No real email was sent.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe checkout, billing portal, webhook, billing-state mutation, or money movement occurred (mock `mvp_mock` plan only).
- No production mode was enabled (`APP_ENV=local` throughout).
- No AWS provisioning occurred.
- No registry push occurred.
- No deployment occurred.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was not merged.
- No package/dependency/lockfile changes.
- No real `.env` file changes.
- No RLS/tenant-context/RBAC gate weakened — the smoke script and bootstrap fix use the same tenant-scoped helpers and real HTTP routes every other client uses; no gate was bypassed to make the script pass (the send-gate/groundedness/approval gates were exercised for real, not skipped).
- No billing/send/groundedness/human-approval gate bypassed.
- The normal dev stack's Docker volumes were never deleted; the smoke script was run repeatedly against real accumulated state, not a disposable fresh volume.

## Remaining blockers

| Item | Status |
|---|---|
| `npm audit` on `master` | Still blocked until `p4/next15-upgrade` is approved/merged or risk is accepted. |
| Staging | Paused. |
| Production | Waits for first real client and separate owner/operator approvals. |
| Real providers | Disabled. Resend/Stripe remain non-live. |
| Repeatable local Docker E2E smoke command | **Resolved by this slice.** |

## Final verdict

- P4-LocalE2E-SmokeScript: **COMPLETE**.
- `docker compose exec backend python -m app.scripts.local_e2e_smoke`: **works, and is truly repeatable** — verified 5 consecutive passes against real accumulated dev-volume state, not just a disposable fresh volume.
- Boss demo: **allowed** (local/mock flow, unaffected).
- Staging: **paused**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
