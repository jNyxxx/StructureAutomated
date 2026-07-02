"""LOCAL/MOCK-ONLY repeatable E2E smoke command for the local Docker demo stack.

Exercises the full local/mock happy path over real HTTP against a running
backend (``http://localhost:8000`` by default) — the same class of routing/
auth/DB bug this project has repeatedly hit was never reachable through
in-process service-layer tests, only through the real FastAPI routes. This
script hits those routes directly instead.

Flow: bootstrap demo tenant -> seed grounding -> login -> contact import ->
contact readback -> campaign create -> contact selection -> draft generation
-> evidence read -> review queue -> approve -> send-gate dry run -> mock send
-> outbound readback -> audit trail -> logout/re-login cycle.

Refuses to run unless ``APP_ENV`` is local/development/demo. Never imported by
a request-handling path — invoke as ``python -m app.scripts.local_e2e_smoke``,
typically via ``docker compose exec -T backend python -m app.scripts.local_e2e_smoke``.

Idempotent: contact import, campaign create, contact selection, draft
generation, review approval, send-gate dry run, and mock send all use fixed,
deterministic Idempotency-Keys scoped to the tenant. Running this script
repeatedly against the same database creates exactly one smoke data chain
instead of growing it on every run. Only the login/logout session ids are
fresh per run, since a session identity is inherently single-use once
revoked.

Idempotent replay responses carry ``idempotency_replay: true`` with the
created-resource field set to ``None`` — only response hashes are persisted,
never payloads (see ``app/services/idempotency.py``). On a replay this script
re-derives state through a GET/list lookup wherever one exists (campaign by
name, draft by review-item lookup, outbound message by draft id, review item
by id) instead of trusting the POST response body. Two steps have no lookup
endpoint at all (contact import, campaign-contact selection) and a third has
no lookup for its specific result (send-gate dry run's stored gate result) —
those replays are trusted at face value and noted as such in the step output.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass, field

import httpx

from app.config import Settings, get_settings
from app.scripts import bootstrap_local_demo, seed_local_grounding

_ALLOWED_SMOKE_ENVS = frozenset({"local", "development", "demo"})

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TENANT_ID = bootstrap_local_demo.DEFAULT_TENANT_ID

_SMOKE_EMAIL = "smoke-e2e@example.com"
_SMOKE_CSV = (
    f"name,email,company,domain\nSmoke E2E,{_SMOKE_EMAIL},Smoke CRE,smoke-e2e.example.com\n"
)
_SMOKE_CAMPAIGN_NAME = "Local E2E Smoke Campaign"

_MAX_LIST_PAGES = 5

_EXPECTED_AUDIT_EVENT_TYPES = (
    "contact_import.completed",
    "campaign.created",
    "campaign.contact_selected",
    "draft.generated",
    "draft.approved",
    "send_gate.passed",
    "outbound_message.sent",
)


class SmokeEnvironmentError(RuntimeError):
    """Raised when the smoke script is invoked outside an allowed local/mock environment."""


class SmokeStepError(RuntimeError):
    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


def ensure_smoke_env_allowed(settings: Settings) -> None:
    if settings.app_env not in _ALLOWED_SMOKE_ENVS:
        raise SmokeEnvironmentError(
            f"Refusing to run local E2E smoke: APP_ENV={settings.app_env!r} is not one "
            f"of {sorted(_ALLOWED_SMOKE_ENVS)}. This smoke command is local/mock/demo-only."
        )


@dataclass
class _SmokeState:
    tenant_id: uuid.UUID
    idempotency_prefix: str
    passed_steps: list[str] = field(default_factory=list)
    import_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    campaign_id: uuid.UUID | None = None
    draft_id: uuid.UUID | None = None
    review_id: uuid.UUID | None = None
    outbound_message_id: uuid.UUID | None = None


def _idempotency_key(state: _SmokeState, step: str) -> str:
    return f"{state.idempotency_prefix}-{step}"


def _headers(token: str, tenant_id: uuid.UUID, *, idempotency_key: str | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _mask(token: str) -> str:
    prefix = token.split(":", 1)[0]
    return f"{prefix}:***"


def _pass(state: _SmokeState, step: str, detail: str) -> None:
    state.passed_steps.append(step)
    print(f"[PASS] {step}: {detail}")


async def _find_in_pages(
    client: httpx.AsyncClient,
    path: str,
    headers: dict,
    list_key: str,
    predicate,
    *,
    extra_params: dict | None = None,
):
    cursor: str | None = None
    for _ in range(_MAX_LIST_PAGES):
        params: dict[str, str | int] = {"limit": 100, **(extra_params or {})}
        if cursor is not None:
            params["cursor"] = cursor
        resp = await client.get(path, headers=headers, params=params)
        resp.raise_for_status()
        body = resp.json()
        for item in body.get(list_key, []):
            if predicate(item):
                return item
        cursor = body.get("page", {}).get("next_cursor")
        if cursor is None:
            break
    return None


async def run_smoke(client: httpx.AsyncClient, *, tenant_id: uuid.UUID, run_id: str) -> _SmokeState:
    state = _SmokeState(tenant_id=tenant_id, idempotency_prefix=f"local-e2e-smoke-{tenant_id}")

    # 1. Bootstrap demo tenant/user/membership/billing/compliance if needed.
    bootstrap_result = await bootstrap_local_demo.run(tenant_id=tenant_id)
    _pass(
        state,
        "bootstrap",
        f"tenant_created={bootstrap_result.tenant_created} "
        f"user_created={bootstrap_result.user_created}",
    )

    # 2. Seed local grounding data if needed.
    seed_result = await seed_local_grounding.run(tenant_id=tenant_id)
    _pass(
        state,
        "grounding_seed",
        "seeded" if seed_result.created else f"skipped ({seed_result.skipped_reason})",
    )

    # 3. Local mock login/session works.
    primary_token = f"token-sentinel:{run_id}"
    resp = await client.get("/auth/me", headers=_headers(primary_token, tenant_id))
    if resp.status_code != 200:
        raise SmokeStepError("login_session", f"GET /auth/me returned {resp.status_code}")
    principal = resp.json()["principal"]
    if principal["tenant_id"] != str(tenant_id) or principal["role"] != "owner":
        raise SmokeStepError("login_session", f"unexpected principal: {principal}")
    _pass(state, "login_session", f"role={principal['role']} token={_mask(primary_token)}")

    # 4. Contact import works. On idempotent replay, import is None with no
    # lookup endpoint available, so import_id stays unknown (excluded from the
    # audit-trail check below) rather than guessed.
    resp = await client.post(
        "/api/v1/imports/contacts",
        headers=_headers(
            primary_token, tenant_id, idempotency_key=_idempotency_key(state, "import")
        ),
        json={"csv_text": _SMOKE_CSV, "source_filename": "local-e2e-smoke.csv"},
    )
    if resp.status_code != 201:
        raise SmokeStepError("contact_import", f"expected 201, got {resp.status_code}: {resp.text}")
    body = resp.json()
    import_body = body.get("import")
    if import_body is None:
        if not body.get("idempotency_replay"):
            raise SmokeStepError("contact_import", f"missing import in non-replay response: {body}")
        _pass(
            state,
            "contact_import",
            "idempotency_replay=true (no lookup endpoint; import_id unknown)",
        )
    else:
        if import_body["status"] != "completed":
            raise SmokeStepError("contact_import", f"unexpected status: {import_body}")
        state.import_id = uuid.UUID(import_body["id"])
        _pass(
            state, "contact_import", f"import_id={state.import_id} status={import_body['status']}"
        )

    # 5. Contact/prospect readback works.
    contact = await _find_in_pages(
        client,
        "/api/v1/contacts",
        _headers(primary_token, tenant_id),
        "contacts",
        lambda c: c["email"] == _SMOKE_EMAIL,
    )
    if contact is None:
        raise SmokeStepError("contact_readback", f"contact {_SMOKE_EMAIL} not found")
    state.contact_id = uuid.UUID(contact["id"])
    _pass(state, "contact_readback", f"contact_id={state.contact_id}")

    # 6. Campaign create works. On idempotent replay, campaign is None; look
    # it back up by its deterministic name instead.
    resp = await client.post(
        "/api/v1/campaigns",
        headers=_headers(
            primary_token, tenant_id, idempotency_key=_idempotency_key(state, "campaign")
        ),
        json={
            "name": _SMOKE_CAMPAIGN_NAME,
            "description": "Automated local E2E smoke campaign.",
            "goal": "acquisition",
            "target_segment": "CRE owners",
            "notes": "LOCAL DEMO MOCK smoke data.",
        },
    )
    if resp.status_code != 201:
        raise SmokeStepError(
            "campaign_create", f"expected 201, got {resp.status_code}: {resp.text}"
        )
    body = resp.json()
    campaign_body = body["campaign"]
    if campaign_body is None:
        if not body.get("idempotency_replay"):
            raise SmokeStepError(
                "campaign_create", f"missing campaign in non-replay response: {body}"
            )
        campaign_body = await _find_in_pages(
            client,
            "/api/v1/campaigns",
            _headers(primary_token, tenant_id),
            "campaigns",
            lambda c: c["name"] == _SMOKE_CAMPAIGN_NAME,
        )
        if campaign_body is None:
            raise SmokeStepError(
                "campaign_create", "idempotent replay but no existing campaign found by name"
            )
    state.campaign_id = uuid.UUID(campaign_body["id"])
    _pass(state, "campaign_create", f"campaign_id={state.campaign_id}")

    # 7. Campaign contact selection works. No GET endpoint exists to
    # re-verify selection state, so an idempotent replay is trusted at face
    # value beyond confirming the envelope shape.
    resp = await client.post(
        f"/api/v1/campaigns/{state.campaign_id}/contacts",
        headers=_headers(
            primary_token, tenant_id, idempotency_key=_idempotency_key(state, "select")
        ),
        json={"contact_id": str(state.contact_id), "status": "selected"},
    )
    if resp.status_code != 201:
        raise SmokeStepError(
            "campaign_contact_select", f"expected 201, got {resp.status_code}: {resp.text}"
        )
    body = resp.json()
    if body["campaign_contact"] is None and not body.get("idempotency_replay"):
        raise SmokeStepError(
            "campaign_contact_select", f"missing campaign_contact in non-replay response: {body}"
        )
    _pass(
        state,
        "campaign_contact_select",
        "contact selected" if body["campaign_contact"] is not None else "idempotency_replay=true",
    )

    # 8. Grounded draft generation works. On idempotent replay, draft is None;
    # recover draft_id via the review queue (every review item carries its
    # draft_id regardless of the draft's own replay state) and re-verify
    # status through the draft detail endpoint.
    resp = await client.post(
        "/api/v1/drafts/generate",
        headers=_headers(
            primary_token, tenant_id, idempotency_key=_idempotency_key(state, "draft")
        ),
        json={"campaign_id": str(state.campaign_id), "contact_id": str(state.contact_id)},
    )
    if resp.status_code != 201:
        raise SmokeStepError("draft_generate", f"expected 201, got {resp.status_code}: {resp.text}")
    body = resp.json()
    draft_body = body["draft"]
    if draft_body is None:
        if not body.get("idempotency_replay"):
            raise SmokeStepError("draft_generate", f"missing draft in non-replay response: {body}")
        review_item = await _find_in_pages(
            client,
            "/api/v1/review/items",
            _headers(primary_token, tenant_id),
            "review_items",
            lambda _item: True,
            extra_params={"campaign_id": str(state.campaign_id)},
        )
        if review_item is None:
            raise SmokeStepError(
                "draft_generate", "idempotent replay but no review item found to recover draft_id"
            )
        draft_id = uuid.UUID(review_item["draft_id"])
        detail = await client.get(
            f"/api/v1/drafts/{draft_id}", headers=_headers(primary_token, tenant_id)
        )
        if detail.status_code != 200:
            raise SmokeStepError(
                "draft_generate", f"draft detail lookup failed: {detail.status_code}"
            )
        draft_body = detail.json()["draft"]
    if draft_body["status"] != "generated":
        raise SmokeStepError(
            "draft_generate",
            f"expected status 'generated', got {draft_body['status']!r} "
            "(local grounding data may be missing)",
        )
    state.draft_id = uuid.UUID(draft_body["id"])
    _pass(state, "draft_generate", f"draft_id={state.draft_id} status={draft_body['status']}")

    # 9. Evidence read works.
    resp = await client.get(
        f"/api/v1/drafts/{state.draft_id}/evidence", headers=_headers(primary_token, tenant_id)
    )
    if resp.status_code != 200:
        raise SmokeStepError("draft_evidence", f"expected 200, got {resp.status_code}")
    evidence = resp.json().get("evidence", [])
    if not evidence:
        raise SmokeStepError("draft_evidence", "no evidence entries returned")
    _pass(state, "draft_evidence", f"{len(evidence)} evidence entries")

    # 10. Review queue contains the draft.
    resp = await client.get(
        "/api/v1/review/items",
        headers=_headers(primary_token, tenant_id),
        params={"campaign_id": str(state.campaign_id)},
    )
    if resp.status_code != 200:
        raise SmokeStepError("review_queue", f"expected 200, got {resp.status_code}")
    review_item = next(
        (
            item
            for item in resp.json().get("review_items", [])
            if item["draft_id"] == str(state.draft_id)
        ),
        None,
    )
    if review_item is None:
        raise SmokeStepError("review_queue", "no review item found for generated draft")
    state.review_id = uuid.UUID(review_item["id"])
    _pass(state, "review_queue", f"review_id={state.review_id} status={review_item['status']}")

    # 11. Human approval action works. On idempotent replay, review_item is
    # None; re-verify approved status via the review item detail endpoint.
    resp = await client.post(
        f"/api/v1/review/items/{state.review_id}/approve",
        headers=_headers(
            primary_token, tenant_id, idempotency_key=_idempotency_key(state, "approve")
        ),
    )
    if resp.status_code != 200:
        raise SmokeStepError("review_approve", f"expected 200, got {resp.status_code}: {resp.text}")
    body = resp.json()
    approve_body = body["review_item"]
    if approve_body is None:
        if not body.get("idempotency_replay"):
            raise SmokeStepError(
                "review_approve", f"missing review_item in non-replay response: {body}"
            )
        detail = await client.get(
            f"/api/v1/review/items/{state.review_id}", headers=_headers(primary_token, tenant_id)
        )
        if detail.status_code != 200:
            raise SmokeStepError(
                "review_approve", f"review item lookup failed: {detail.status_code}"
            )
        approve_body = detail.json()["review_item"]
    if approve_body["status"] != "approved":
        raise SmokeStepError("review_approve", f"unexpected status: {approve_body}")
    _pass(state, "review_approve", "status=approved")

    # 12. Send-gate dry run passes. No GET endpoint exists to look a stored
    # gate result back up, so an idempotent replay's status is trusted at face
    # value; mock_only stays independently verifiable since it defaults True
    # on both the fresh and replayed result (app/services/send_gate.py).
    resp = await client.post(
        "/api/v1/send-gate/dry-run",
        headers=_headers(primary_token, tenant_id, idempotency_key=_idempotency_key(state, "gate")),
        json={"draft_id": str(state.draft_id)},
    )
    if resp.status_code != 200:
        raise SmokeStepError(
            "send_gate_dry_run", f"expected 200, got {resp.status_code}: {resp.text}"
        )
    body = resp.json()
    if not body.get("mock_only"):
        raise SmokeStepError("send_gate_dry_run", f"unexpected gate result: {body}")
    gate_body = body["send_gate_result"]
    if gate_body is None:
        if not body.get("idempotency_replay"):
            raise SmokeStepError(
                "send_gate_dry_run", f"missing send_gate_result in non-replay response: {body}"
            )
        _pass(
            state,
            "send_gate_dry_run",
            "idempotency_replay=true mock_only=true (no lookup endpoint)",
        )
    else:
        if gate_body["status"] != "passed":
            raise SmokeStepError("send_gate_dry_run", f"unexpected gate result: {body}")
        _pass(state, "send_gate_dry_run", "status=passed mock_only=true")

    # 13. Mock send intent returns a safe mock-only status. On idempotent
    # replay, result is None; step 14 recovers the outbound message by
    # draft_id instead of by id, since that lookup works in both cases.
    resp = await client.post(
        "/api/v1/send-intents",
        headers=_headers(primary_token, tenant_id, idempotency_key=_idempotency_key(state, "send")),
        json={"draft_id": str(state.draft_id)},
    )
    if resp.status_code != 201:
        raise SmokeStepError("mock_send", f"expected 201, got {resp.status_code}: {resp.text}")
    send_body = resp.json()
    if send_body.get("mock_only") is not True:
        raise SmokeStepError(
            "mock_send",
            f"expected mock_only=true, got {send_body} "
            "(refusing to treat a non-mock send result as a pass)",
        )
    result_body = send_body.get("result")
    if result_body is None:
        if not send_body.get("idempotency_replay"):
            raise SmokeStepError("mock_send", f"missing result in non-replay response: {send_body}")
        _pass(state, "mock_send", "idempotency_replay=true mock_only=true")
    else:
        if result_body.get("status") != "mock_sent":
            raise SmokeStepError(
                "mock_send",
                f"expected status='mock_sent', got {send_body} "
                "(refusing to treat a non-mock send result as a pass)",
            )
        _pass(
            state,
            "mock_send",
            f"outbound_message_id={result_body['outbound_message_id']} status=mock_sent",
        )

    # 14. Outbound message readback works. Matched by draft_id (not the
    # mock-send response's id, which is unavailable on idempotent replay);
    # this also derives outbound_message_id for the audit-trail check below.
    outbound = await _find_in_pages(
        client,
        "/api/v1/outbound-messages",
        _headers(primary_token, tenant_id),
        "outbound_messages",
        lambda m: m["draft_id"] == str(state.draft_id),
    )
    if outbound is None or outbound["status"] != "mock_sent":
        raise SmokeStepError("outbound_readback", f"unexpected outbound message: {outbound}")
    state.outbound_message_id = uuid.UUID(outbound["id"])
    _pass(
        state,
        "outbound_readback",
        f"outbound_message_id={state.outbound_message_id} status=mock_sent",
    )

    # 15. Audit trail contains expected events for this run's objects.
    # contact_import.completed is only checked when import_id is known — an
    # idempotent replay of the import step never returns an id to match on.
    object_ids = {
        str(state.contact_id),
        str(state.campaign_id),
        str(state.draft_id),
        str(state.review_id),
        str(state.outbound_message_id),
    }
    expected_event_types = set(_EXPECTED_AUDIT_EVENT_TYPES)
    if state.import_id is not None:
        object_ids.add(str(state.import_id))
    else:
        expected_event_types.discard("contact_import.completed")
    found_types: set[str] = set()
    cursor: str | None = None
    for _ in range(_MAX_LIST_PAGES):
        params: dict[str, str | int] = {"limit": 100}
        if cursor is not None:
            params["cursor"] = cursor
        resp = await client.get(
            "/api/v1/audit-events", headers=_headers(primary_token, tenant_id), params=params
        )
        if resp.status_code != 200:
            raise SmokeStepError("audit_trail", f"expected 200, got {resp.status_code}")
        body = resp.json()
        for event in body.get("audit_events", []):
            if event.get("object_id") in object_ids:
                found_types.add(event["event_type"])
        cursor = body.get("page", {}).get("next_cursor")
        if cursor is None or expected_event_types <= found_types:
            break
    missing = expected_event_types - found_types
    if missing:
        raise SmokeStepError(
            "audit_trail", f"missing expected audit event types: {sorted(missing)}"
        )
    _pass(state, "audit_trail", f"{len(found_types)} expected event types present")

    # 16. Logout / re-login cycle still works.
    resp = await client.post("/auth/logout", headers=_headers(primary_token, tenant_id))
    if resp.status_code != 200 or resp.json().get("revoked", 0) < 1:
        raise SmokeStepError("logout", f"expected revoked>=1, got {resp.status_code}: {resp.text}")
    resp = await client.get("/auth/me", headers=_headers(primary_token, tenant_id))
    revoked_code = resp.json().get("error", {}).get("code")
    if resp.status_code != 401 or revoked_code != "AUTH_SESSION_REVOKED":
        raise SmokeStepError(
            "logout",
            f"expected revoked session to be rejected, got {resp.status_code}: {resp.text}",
        )
    relogin_token = f"token-sentinel:{run_id}-b"
    resp = await client.get("/auth/me", headers=_headers(relogin_token, tenant_id))
    if resp.status_code != 200:
        raise SmokeStepError("relogin", f"fresh login failed: {resp.status_code}: {resp.text}")
    _pass(state, "logout_relogin", f"revoked old session, fresh login={_mask(relogin_token)} ok")

    return state


async def run(*, base_url: str, tenant_id: uuid.UUID) -> _SmokeState:
    ensure_smoke_env_allowed(get_settings())
    run_id = uuid.uuid4().hex[:12]
    async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
        return await run_smoke(client, tenant_id=tenant_id, run_id=run_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-id",
        type=uuid.UUID,
        default=DEFAULT_TENANT_ID,
        help="Target tenant UUID (default: local demo tenant).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL to smoke-test (default: http://localhost:8000).",
    )
    args = parser.parse_args(argv)

    try:
        state = asyncio.run(run(base_url=args.base_url, tenant_id=args.tenant_id))
    except SmokeEnvironmentError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except SmokeStepError as exc:
        print(f"[FAIL] {exc.step}: {exc.detail}", file=sys.stderr)
        print(f"SMOKE FAILED at {exc.step}", file=sys.stderr)
        return 1

    step_count = len(state.passed_steps)
    print(f"SMOKE PASSED ({step_count}/{step_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
