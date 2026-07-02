# P4-LocalDockerE2E-Fix-4-GroundedHappyPathSeed

**Date:** 2026-07-02
**Branch:** `master`
**Base commit:** `a757e23 fix(backend): return full draft rows after generation`
**Status:** COMPLETE. The full grounded draft happy path now works end to end in local Docker: seeded grounding data produces a `generated` draft, human approval, send-gate dry run, mock send intent, outbound read, and audit trail all pass.

## Scope

Local-only backend fix, local/mock seed, and evidence update. `p4/next15-upgrade` was not merged. No package, real `.env`, secret, AWS, registry, deployment, staging, production, provider, Stripe, SMS, or scraping work was performed. Auth/RBAC/RLS/tenant isolation, billing gates, idempotency, send gates, safety/groundedness gates, and human approval were preserved and exercised, not bypassed.

## Blocker summary

Before this slice, `POST /api/v1/drafts/generate` always returned `status: "needs_regeneration"` in local Docker (see [evidence/phase-4-local-docker-e2e-fix-3-draft-generation.md](phase-4-local-docker-e2e-fix-3-draft-generation.md)). Because a draft only enters the human-review queue when generation succeeds with `status: "generated"`, the review → approval → send-gate → mock-send → outbound → audit happy path was never reached.

## Root cause

1. **Missing local grounding data (primary cause).** The local Docker tenant had zero `knowledge_documents`/`knowledge_chunks` and no research artifact for the seeded contact. `DraftGenerationService.generate_draft` calls `RAGGroundingService.retrieve_grounding_context` (`backend/app/services/rag_grounding.py`), which returns the tenant's first three active knowledge chunks. With none, it returned an empty chunk list. `GroundednessService.evaluate_draft_groundedness` (`backend/app/services/groundedness.py:72-76`) treats `len(chunks) == 0` as `status="failed"`, `reason_code="no_evidence_provided"`, which forces `draft_generation.py:396-402` to create a `needs_regeneration` draft and skip the review queue. This is the groundedness gate working correctly (fail-closed), not a bug — the fix is to seed valid grounding data, not to weaken the gate.
2. **A second, previously-deferred code bug surfaced once the happy path reached further.** After seeding, `POST /api/v1/send-gate/dry-run` and `GET /api/v1/audit-events` both returned `500 Internal Server Error` with `AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'id'`. This is the same `RETURNING(Model).scalars()` / `SELECT(Model).scalars()` row-mapping bug documented in fix-1/2/3, in two repositories fix-3 explicitly listed as "deferred same-pattern risk": `backend/app/repositories/sending_repo.py` (`SendingRepository.create_gate_result`, and all other methods) and `backend/app/audit/repository.py` (`AuditRepository.list_recent_bounded`). These paths had never been exercised against a real Postgres connection before this slice (only exercised via in-memory fakes in unit tests), so the deferred risk had never actually failed until now.

## Fix / seed summary

### 1. Deterministic local grounding seed (new)

- `backend/app/scripts/__init__.py` (new) — package marker, docstring-only.
- `backend/app/scripts/seed_local_grounding.py` (new) — env-guarded, idempotent CLI:
  - Refuses to run unless `APP_ENV` is `local`, `development`, or `demo` (`ensure_seed_env_allowed`); fails closed on `staging`, `production`, or any unrecognized value.
  - Builds a `CurrentPrincipal` mirroring the existing local-mock owner identity (`backend/app/auth/local_mock.py`) for a target tenant (default: the demo tenant provisioned by the P3-2 local DB seed, `22222222-2222-2222-2222-222222222222`, overridable via `--tenant-id`).
  - Ingests one clearly-labeled document (`SEED_DOC_TITLE = "LOCAL DEMO MOCK - CRE Outreach Grounding Guidelines"`, content prefixed `LOCAL DEMO MOCK:` throughout) through the **existing gated** `RAGGroundingService.add_document` path — the same RBAC (`knowledge:manage`) check and `knowledge.document_created` / `knowledge.document_chunked` audit events that a real tenant document upload would produce. No new bypass path was added.
  - Idempotent: checks `KnowledgeRepository.get_document_by_title` first; a second run reports `SKIPPED (already_seeded)` and makes no changes.
  - Content contains no secrets, no real client data, and is pinned by a unit test to never contain the groundedness/safety marker substrings (`unsupported claim`, `hallucination`, `fake claim`, `ignore previous instructions`, `system prompt`, `jailbreak`).
  - Invocation: `docker compose exec backend python -m app.scripts.seed_local_grounding`.

### 2. Row-mapping fix, extended (`backend/app/repositories/knowledge_repo.py`)

Rewrote every method (not just the two insert paths) to explicit returned/selected columns + `Result.mappings()`, matching the pattern already applied to `draft_repo.py`/`safety_repo.py`/`review_repo.py` in fix-3: `create_document`, `get_document`, `update_document`, `create_chunks`, `list_chunks_for_grounding`, `get_research_artifact_for_contact`. Added a new read-only `get_document_by_title` method for the seed's idempotency check. The full-file rewrite (not just the two write paths originally flagged) was necessary because `list_chunks_for_grounding` and `get_research_artifact_for_contact` are called immediately after seeding, on the same code path fix-4 needed to prove works.

### 3. Row-mapping fix, newly discovered (`backend/app/repositories/sending_repo.py`, `backend/app/audit/repository.py`)

Rewrote every method in both files to explicit columns + `Result.mappings()`, following the identical established pattern:

```text
.returning(Model).scalars().one()   ->   .returning(*_COLUMNS).mappings().one()
select(Model).scalars().first()     ->   select(*_COLUMNS).mappings().first()
```

`sending_repo.py`: `create_gate_result`, `get_gate_result_for_draft`, `create_outbound_message`, `get_outbound_message_by_draft`, `list_outbound_messages`, `get_outbound_message_by_id`, `update_outbound_message_status`.
`audit/repository.py`: `list_recent_bounded` (the unused, uncalled `list_recent` helper was left as-is — dead code, not exercised by any caller, out of scope).

### Why safety/groundedness/approval/send-gates are preserved

- No gate logic changed. `GroundednessService`, `SafetyService`, `ReviewService.approve_draft`, and `SendGateService.evaluate_gate` are untouched. The seed produces valid evidence that the *existing* rules already accept — it does not change what the rules accept.
- The seed only calls `RAGGroundingService.add_document`, the same RBAC- and audit-gated path any tenant would use to add knowledge content; it never writes to `drafts`, `review_items`, `safety_gate_results`, or `outbound_messages` directly, and it does not go through `tenant_session` with elevated privilege — it uses the same tenant-scoped connection and role as any other request.
- Human approval was exercised, not bypassed: `POST /api/v1/review/items/{id}/approve` was called and required a pending, ungrounded-safe review item.
- The send gate was exercised, not bypassed: `POST /api/v1/send-gate/dry-run` re-ran every gate check (RBAC, billing, draft state, review approval, tenant match, suppression, safety/groundedness, duplicate-send) against real persisted rows before returning `passed`.
- Mock send intent remained mock-only: `POST /api/v1/send-intents` used `MockSenderService` / `MockEmailSendProvider`; the audit record shows `"provider":"mock"`, `"provider_status":"accepted"`, and every response carries `"mock_only": true`.

## Tests added/updated

- `backend/tests/test_seed_local_grounding.py` (new, 6 tests): env-guard refusal (`staging`/`production`/unknown) and allow-list (`local`/`development`/`demo`); seed principal is the local-mock owner with `knowledge:manage`; seed content contains none of the six gate marker substrings; seeding twice is idempotent (`created=True` then `skipped_reason="already_seeded"`); seeded content independently passes `SafetyService.evaluate_grounding_safety` and `GroundednessService.evaluate_draft_groundedness` when run for real against the seeded chunks.
- `backend/tests/test_grounded_happy_path_e2e.py` (new, 2 tests):
  - `test_seeded_grounding_produces_generated_draft_through_mock_send` — full chain at the service level with the same fully-wired composition as the routers (`safety_service`, `groundedness_service`, `review_store`, `compliance` all present, matching `drafts.py`/`review.py`/`sending.py`): seed → `generate_draft` (`status="generated"`, evidence linked, 3 passing gate results, pending review item) → `approve_draft` (`status="approved"`) → `evaluate_gate` (`status="passed"`, no outbound message yet) → `send_approved_draft` (`status="mock_sent"`) → outbound record readable → audit event set contains the whole chain and **no** `safety.gate_failed` / `send_gate.failed` / `draft.needs_regeneration` events.
  - `test_generate_draft_with_no_grounding_data_needs_regeneration` — regression proof: with the same fully-wired services but no seeded grounding data, generation still returns `needs_regeneration` with `reason_code="no_evidence_provided"` and creates **no** review item. Proves the seed is what flips the outcome, and that the fail-closed behavior is untouched.
- `backend/tests/test_repository_row_mapping.py` (extended, +5 tests): `KnowledgeRepository.create_document`/`create_chunks` (added in this slice's earlier pass), `SendingRepository.create_gate_result`/`create_outbound_message`, `AuditRepository.list_recent_bounded` — each asserts the repository never calls `.scalars()` and always returns a fully-populated record via `.mappings()`.

Targeted result:

```text
python -m pytest tests/test_repository_row_mapping.py tests/test_grounded_happy_path_e2e.py tests/test_seed_local_grounding.py -v
14 passed
```

## Gate results

Backend:

| Gate | Result |
|---|---|
| Ruff | PASS |
| Black check | PASS |
| mypy | PASS |
| pytest | PASS — 751 tests |

Frontend (no frontend source changed; run per spec):

| Gate | Result |
|---|---|
| lint | PASS |
| typecheck (`tsc --noEmit`) | PASS |
| test (vitest) | PASS — 141 tests |
| build (`next build`) | PASS — 27 static/dynamic routes |

Docker:

| Check | Result |
|---|---|
| `docker compose down --remove-orphans` (no `-v`, volumes preserved) | PASS |
| `docker compose up -d --build` | PASS |
| `docker compose ps` | all services up; `db` healthy |
| `GET /health` | `{"status":"ok"}` |
| `GET /live` | `{"status":"alive","service":"backend"}` |
| `GET /ready` | `{"status":"ok","environment":"local","checks":{"database":"ok","migrations":"up_to_date","rate_limit_backend":"in_memory"}}` |
| Frontend route smoke (`/review-queue`, `/billing`, `/settings/suppression`, `/settings/compliance`) | all HTTP 200 |

## Local happy-path E2E result

All steps run against the live Docker stack (tenant `22222222-2222-2222-2222-222222222222`, mock auth token `token-sentinel`):

1. Contact import — `POST /api/v1/imports/contacts` → 201, `status: "completed"`.
2. Campaign create — `POST /api/v1/campaigns` → 201.
3. Campaign contact selection — `POST /api/v1/campaigns/{id}/contacts` → 201.
4. **Baseline confirmed first:** draft generation before seeding → `status: "needs_regeneration"` (reproduces the fix-3 blocker exactly, on a fresh campaign/contact pair).
5. Seed: `docker compose exec backend python -m app.scripts.seed_local_grounding` → `SEEDED: document_id=... chunk_count=2 tenant_id=22222222-...`. Re-run → `SKIPPED (already_seeded): ...` (idempotency proof).
6. Draft generation after seeding — `POST /api/v1/drafts/generate` → 201, **`status: "generated"`**.
7. Draft evidence — `GET /api/v1/drafts/{id}/evidence` → 200, 2 `knowledge_chunk` evidence rows referencing the seeded chunks.
8. Review queue — `GET /api/v1/review/items?status=pending_review` → 200, one item for the draft.
9. Human approval — `POST /api/v1/review/items/{id}/approve` → 200, `status: "approved"`.
10. Send-gate dry run — `POST /api/v1/send-gate/dry-run` → 200, `status: "passed"` (after the `sending_repo.py` fix; returned 500 before it).
11. Mock send intent — `POST /api/v1/send-intents` → 201, `status: "mock_sent"`, `mock_only: true`.
12. Outbound read — `GET /api/v1/outbound-messages` → 200, message `status: "mock_sent"`.
13. Audit trail — `GET /api/v1/audit-events` → 200 (after the `audit/repository.py` fix; returned 500 before it), full chain visible: `knowledge.document_created`, `knowledge.document_chunked`, `safety.gate_passed` (×2, prompt_injection/source_trust and groundedness), `draft.generated`, `draft.approved`, `send_gate.passed`, `outbound_message.sent`. The earlier baseline attempt's `safety.gate_failed` (`no_evidence_provided`) and `draft.needs_regeneration` events are also visible, correctly documenting the pre-seed fail-closed state.
14. Billing/access UI (`/billing`) and compliance/suppression UI (`/settings/compliance`, `/settings/suppression`) — both load HTTP 200 through the frontend container, unaffected by these backend-only changes.
15. No real provider action occurred at any step (see Safety confirmation).

## Safety confirmation

- No live email was sent — `MockSenderService` / `MockEmailSendProvider` only; audit shows `"provider":"mock"`, all responses carry `"mock_only": true`.
- No Resend live send occurred.
- No cold outreach live send occurred.
- No Stripe money movement occurred.
- No production mode was enabled — `APP_ENV=local` throughout; the seed script's env guard independently refuses `staging`/`production`.
- No AWS provisioning occurred.
- No container image was pushed to any registry.
- No SMS or live scraping occurred.
- `p4/next15-upgrade` was **not** merged (verified before and after this slice).
- Groundedness was **not** bypassed — the seed satisfies the existing rule (≥1 valid, citable evidence chunk); the gate logic in `groundedness.py` is unchanged, and the regression test proves an unseeded tenant still gets `needs_regeneration`.
- Human approval was **not** bypassed — `POST /api/v1/review/items/{id}/approve` was called and required a real pending review item with all three passing gate results.
- The send gate was **not** bypassed — `POST /api/v1/send-gate/dry-run` re-evaluated every check against persisted state before returning `passed`.

## Remaining blockers

| Item | Status |
|---|---|
| `npm audit` on `master` | Still blocked until William approves/merges `p4/next15-upgrade`. |
| Staging | Paused by William. |
| Production | Waits for first real client. |
| Fresh-volume tenant bootstrap | The seed's tenant precondition depends on the tenant/user/membership rows manually provisioned in P3-2 (`docs/evidence/phase-3-2-live-db-smoke.md`); those rows live only in the current `automatedstructure_db_data` Docker volume, not in a committed migration/seed. On a fresh volume (`docker compose down -v`), the seed script fails closed with an actionable `SeedPreconditionError` pointing at the P3-2 doc rather than silently succeeding or crashing. A committed local tenant-bootstrap seed is a reasonable future slice but was out of scope here (fix-4 was scoped to grounding data, not tenant provisioning). |
| Other same-pattern row-mapping risk | `backend/app/repositories/research_repo.py` still uses the unfixed `.scalars()` pattern. It is not exercised by this happy path (only touched when a chunk's `source_type == "research_artifact"`, which the seed does not create) and remains a documented, deferred risk for the next slice that exercises the research-artifact evidence path in Docker. |

## Verification before commit

- `git diff --check` — clean.
- `git status --short` — only the files listed below.
- `p4/next15-upgrade` confirmed **not** merged (`git log --oneline -5` on `master` shows no merge commit from that branch).
- No package/lockfile changes.
- No real `.env` file changes.
- No deployment/provider/production changes.
- Changed docs/source grepped for "production enabled" / "deployed" / "real sending enabled" / "money movement enabled" — no matches.
- Changed docs/source grepped for secret-looking values — no matches (seed content is clearly labeled `LOCAL DEMO MOCK` throughout, contains no keys/tokens/credentials).
- No registry push, no deployment.

## Files changed

| File | Change |
|---|---|
| `backend/app/repositories/knowledge_repo.py` | Row-mapping fix (all methods) + new `get_document_by_title`. |
| `backend/app/repositories/sending_repo.py` | Row-mapping fix (all methods) — newly discovered blocker. |
| `backend/app/audit/repository.py` | Row-mapping fix (`list_recent_bounded`) — newly discovered blocker. |
| `backend/app/scripts/__init__.py` | New — local/mock script package marker. |
| `backend/app/scripts/seed_local_grounding.py` | New — env-guarded, idempotent local grounding seed CLI. |
| `backend/tests/test_repository_row_mapping.py` | Extended — knowledge/sending/audit row-mapping regression tests. |
| `backend/tests/test_seed_local_grounding.py` | New — seed unit tests. |
| `backend/tests/test_grounded_happy_path_e2e.py` | New — chained happy-path + fail-closed regression tests. |
| `docs/PHASE_4_IMPLEMENTATION_PLAN.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`, `docs/DOCUMENTATION_MANIFEST.md` | Tracking updates for this slice. |

## Recommendation

Local Docker happy-path E2E is now complete end to end. Next candidates (all still gated by owner/operator values per `docs/LAUNCH_BLOCKERS_AND_OWNER_DECISIONS.md`): a committed local tenant-bootstrap seed (removes the fresh-volume dependency on the manual P3-2 seed), the deferred `research_repo.py` row-mapping fix if a future slice exercises the research-artifact evidence path in Docker, and resuming Phase 4 staging slices once P4-1 values are locked.

## Final verdict

- P4-LocalDockerE2E-Fix-4-GroundedHappyPathSeed: **COMPLETE**.
- Grounded draft happy path: **WORKS** (`status: "generated"` with valid, citable evidence).
- Review / send-gate / mock-send / audit path: **COMPLETE** (approval → dry run → mock send → outbound read → audit trail, all verified against the live Docker stack).
- Boss demo: **allowed**.
- Staging: **paused by William**.
- Production: **waits for first real client**.
- `p4/next15-upgrade`: **not merged**.
