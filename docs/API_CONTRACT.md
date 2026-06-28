# API Contract

**Purpose:** Implementation contract for the HTTP API — conventions, response/error envelope, pagination, idempotency, rate limits, webhook verification, and the endpoint matrix. Routes listed here are the only required MVP routes; do not invent others.
**Source sections:** Master guide §11 (API contract summary), §10 (error envelope, pagination, idempotency, rate limits, health), §17 (webhook verification).
**Status:** Draft
**Related docs:** [AUTH_AND_RBAC](AUTH_AND_RBAC.md) (auth/permission per route) · [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`idempotency_keys`) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (send-gate) · [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md) (webhook processing)

---

## 1. Conventions

- All paths versioned under `/api/v1`.
- **Every endpoint must define** auth, permission, request schema, response schema, rate limit, idempotency behavior, audit event, and security tests **before implementation**.
- Frontend role checks are UX only — backend enforces authorization ([AUTH_AND_RBAC](AUTH_AND_RBAC.md)).

## 2. Common responses

```json
{ "data": {} }
```
```json
{ "data": [], "page": { "next_cursor": null, "limit": 25 } }
```

## 3. Error envelope

```json
{ "error": { "code": "PERMISSION_DENIED", "message": "You do not have access to this resource.", "details": {}, "request_id": "req_..." } }
```

- Do **not** leak whether a cross-tenant object exists. Return generic 404/403 per policy.

## 4. Pagination & filtering

- Cursor pagination by default. Default page size **25**, max **100**.
- All list endpoints filter by tenant in SQL **and** RLS.
- Validate filter fields with Pydantic/Zod. Stable ordering required.

## 5. Idempotency

Required for unsafe operations (CLAUDE rule 7). Keys:

| Surface | Key |
|---|---|
| API actions | `Idempotency-Key` header |
| Worker actions | deterministic job keys |
| Webhooks | provider event IDs |
| Outbound messages | unique send-intent keys |

Store request hash, response hash, status code, scope, tenant, expiry, status (`idempotency_keys` table). A replay with a **different** body returns `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`.

## 6. Rate limits (minimum)

Clerk session exchange/status/logout (by IP + user/session) · imports (by tenant) · agent runs/tool calls (by tenant/campaign) · send scheduling (by tenant/campaign/mailbox) · webhooks (by provider/source) · mock billing transitions/status. Production may use Redis/WAF/provider limits; local may use in-memory/DB if behavior matches.

## 7. Webhook verification

- **Stripe (P3-6d foundation):** `POST /api/v1/webhooks/stripe` verifies the raw request body using the `Stripe-Signature` header before parsing event fields. The default runtime dependency remains fail-closed until approved webhook-secret resolution is added. It normalizes only safe billing event references, performs provider-event-id idempotency through a boundary, and does not mutate tenant billing state.
- **n8n internal:** HMAC or shared-secret header, rotatable, fail closed.
- **Resend (P3-5g foundation):** `POST /api/v1/webhooks/resend` verifies the raw request body using the Resend/Svix signature header set before parsing event fields. The default runtime dependency remains fail-closed until approved webhook-secret resolution is added. It normalizes only safe delivery/bounce/complaint/deferred/failed/suppressed fields and ignores open/click tracking.
- **Future Twilio/mailbox:** provider-specific signature verification before parsing.
- Webhooks must be verified, deduped by provider event ID, and then processed. P3-5g uses an in-memory boundary only; durable stored-first persistence is still deferred to a later approved slice. Processing detail → [WORKERS_QUEUE_AND_WEBHOOKS](WORKERS_QUEUE_AND_WEBHOOKS.md).

## 8. Required endpoint groups

| Group | Endpoints |
|---|---|
| Auth/session | Clerk session exchange/status, `POST /auth/logout`, `GET /sessions`, `DELETE /sessions/{id}` for app-side revocation/audit only |
| Tenant/team | `GET/PATCH /tenants/current`, `GET/POST/PATCH/DELETE /memberships` |
| Contacts/imports/prospects | `GET/POST/PATCH/DELETE /contacts`, `POST /imports/csv`, `GET /imports/{id}`, `GET /prospects` |
| Campaigns/runs | `POST/GET/PATCH /campaigns`, `GET /campaigns/{id}`, `POST /campaigns/{id}/prospects`, `POST /campaigns/{id}/runs`, `GET /campaign-runs/{id}` |
| Drafts/review | `POST /drafts/generate`, `GET /drafts/{id}`, `POST /drafts/{id}/groundedness-check`, `GET /review-queue`, approve/reject/edit review item |
| Sending/messages | `POST /send-intents/{id}/schedule`, `GET /outbound-messages`, `POST /send-gate/dry-run` |
| Deliverability/mailboxes | `GET /deliverability`, `GET/POST/PATCH /mailboxes` |
| Compliance/suppression | `GET/PUT /compliance/profile`, `GET/POST /suppressions`, `POST /suppressions/{id}/reinstate` |
| Integrations/webhooks | `GET /integrations`, `POST /integrations/{provider}/connect`, `POST /webhooks/n8n/{name}`, `POST /webhooks/resend` (verification/normalization foundation only), `POST /webhooks/stripe` (verification/normalization foundation only; no checkout or billing-state mutation) |
| Billing/usage | `GET /billing/subscription`, mock billing state transition endpoint for local/demo admins, `GET /usage`, `POST /billing/checkout-session` and `POST /billing/portal-session` as fail-closed skeletons only; real checkout/portal deferred |
| Audit/privacy | `GET /audit-events`, `POST /privacy/export`, `POST /privacy/delete` |
| Platform/admin | `GET /platform/tenants`, `POST /platform/support-access` |
| Demo/future | `POST /mock/outcomes`, `GET /signals`, `POST /signals/mock` (where environment allows) |
| Health | `GET /health/live`, `GET /health/ready`, `GET /health/deep` |

- **`POST /send-gate/dry-run` must never send.** It returns the same decision-engine result workers use, so admins/reviewers can debug blocked sends.

## 9. Health checks

| Endpoint | Purpose |
|---|---|
| `GET /health/live` | Process alive; no DB required. |
| `GET /health/ready` | DB reachable, migrations current, queue reachable. |
| `GET /health/deep` | Admin-only: DB, queue, secrets, provider mocks, worker lag. |
