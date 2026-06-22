# Database Schema

**Purpose:** Implementation contract for the multi-tenant PostgreSQL model — invariants, status domains, table groups, hardening rules, DDL patterns, indexes, forced RLS, and the acceptance checklist. DDL here is **patterns only**; Alembic migrations are the schema authority in code.
**Source sections:** Master guide §7 (core database model), §16 (embedding tables/safety).
**Status:** Draft
**Related docs:** [CLAUDE](../CLAUDE.md) (rules 1–6) · [AUTH_AND_RBAC](AUTH_AND_RBAC.md) (tenant context, RBAC) · [BILLING_STATE_MACHINE](BILLING_STATE_MACHINE.md) (access states) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (suppression/send intent) · [AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md) (embedding service) · [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md) (retention/purge) · [TESTING_AND_AUDIT](TESTING_AND_AUDIT.md)

---

## 1. Implementation authority

1. This doc defines the required shape and invariants.
2. **Alembic migrations are the only schema authority in code.**
3. SQLAlchemy models may support migration typing, but runtime data access uses **tenant-scoped repositories** only.
4. A table is not accepted until RLS, constraints, indexes, seed data, and tests exist where applicable.

## 2. Tenant-first principles

- PostgreSQL **16+**. UUID primary keys.
- `tenant_id UUID NOT NULL` on **every** tenant-owned table. Never mix `client_id`/`workspace_id`/`account_id`.
- `citext` for emails/case-insensitive identity; `pgvector` for embeddings; `pgcrypto` for crypto helpers.
- Every tenant-owned table: **RLS enabled and forced**.
- Every mutable table: `created_at`, `updated_at`, and `deleted_at` where needed. **Soft-delete** user-facing business data by default.
- Audit logs are append-only, redacted, protected from update/delete.
- FKs prevent orphan tenant data. Status fields use CHECK constraints for MVP unless enums are clearly needed.
- PII and embeddings must be exportable, deletable, anonymizable, or purgeable by policy.
- **JSONB discipline:** business-critical fields (filtering, billing, gates, dashboards, permissions, compliance, workers, reporting) must be real columns, not only inside `metadata`/`config`.

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
```

## 3. Required status domains

| Object | States |
|---|---|
| tenant | trial, active, past_due, grace, locked, canceled, deleted |
| subscription | trialing, active, past_due, grace, canceled, incomplete, incomplete_expired, unpaid |
| internal access | trialing, active, past_due_grace, past_due_locked, canceled, chargeback_locked, unpaid_locked, incomplete_locked |
| contact | active, suppressed, unsubscribed, deleted |
| lead | new, working, qualified, meeting_booked, won, lost, disqualified |
| campaign | draft, queued, running, paused, completed, archived |
| draft | generated, needs_review, approved, rejected, scheduled, sent, blocked |
| review | pending, approved, rejected, changes_requested, expired |
| send intent | pending, blocked, scheduled, leased, sent, failed, canceled |
| outbound message | queued, sending, sent, failed, bounced, replied, canceled |
| mailbox | created, dns_pending, warming, warm, paused, degraded, blocked, retired |
| job | queued, leased, running, succeeded, failed, dead_letter, canceled |
| webhook | received, verified, processing, processed, duplicate, failed, ignored |
| legal review | not_reviewed, approved, rejected, needs_changes |

## 4. Core table groups

| Group | Tables |
|---|---|
| Tenancy/auth/support | `tenants`, `users`, `tenant_memberships`, `sessions`, `password_reset_tokens`, `email_verification_tokens`, `admin_support_access`, `api_keys` |
| Billing/usage | `plans`, `tenant_subscriptions`, `invoices`, `payment_events`, `stripe_webhook_events`, `usage_counters`, `quota_events` |
| CRM/prospects/outcomes | `contacts`, `prospects`, `leads`, `pipeline_stages`, `consent_ledger`, `suppression_entries`, `outcome_events` |
| RAG/research | `research_sources`, `research_snippets`, `knowledge_embeddings`, `brand_voice_examples` |
| Campaigns/agents/review | `outreach_campaigns`, `campaign_prospects`, `agent_runs`, `agent_actions`, `outreach_drafts`, `groundedness_verdicts`, `review_queue_items`, `review_decisions` |
| Sending/deliverability | `domains`, `mailboxes`, `mailbox_warmup_states`, `send_intents`, `outbound_messages`, `reply_events`, `followup_tasks`, `deliverability_snapshots` |
| Integrations/jobs/audit/privacy | `integration_connections`, `integration_credentials`, `agent_tool_permissions`, `webhook_events`, `upload_files`, `import_jobs`, `import_rows`, `jobs`, `idempotency_keys`, `audit_events`, `deletion_requests`, `export_requests` |
| Compliance/send gate | `tenant_compliance_profiles`, `send_gate_results` |
| Future signals | `signal_events`, `trigger_rules` (placeholder/foundation only) |

## 5. Required hardening rules

| Area | Rule |
|---|---|
| Naming | `tenant_id` consistently on all tenant-owned tables. |
| Duplicate sends | `send_intents` has a deterministic unique key per tenant/campaign/prospect/sequence step or draft version. |
| Outbound messages | `outbound_messages.send_intent_id` is unique → provider retries idempotent. |
| Suppression | Works by contact, email, phone, and channel; survives re-import. |
| Global RAG | Global embeddings require explicit approval + PII-scrub fields. |
| Billing access | Store provider status **separately** from internal access state. |
| Audit immutability | Normal app roles cannot UPDATE/DELETE `audit_events`. |
| JSONB discipline | Business-critical fields are real columns. |
| Indexes | Tenant tables require composite **tenant-first** indexes. |

## 6. DDL patterns (invariant-bearing — patterns only)

### Tenants, users, memberships
```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL,
  legal_name VARCHAR(255),
  primary_domain VARCHAR(255),
  niche VARCHAR(100) NOT NULL DEFAULT 'commercial_real_estate',
  status VARCHAR(50) NOT NULL CHECK (status IN ('trial','active','past_due','grace','locked','canceled','deleted')),
  timezone VARCHAR(100) NOT NULL DEFAULT 'America/New_York',
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX ux_tenants_primary_domain
ON tenants (lower(primary_domain)) WHERE primary_domain IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email CITEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  full_name VARCHAR(255),
  mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE tenant_memberships (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) NOT NULL CHECK (role IN ('owner','admin','marketer','reviewer','viewer','billing_admin')),
  permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id)
);
CREATE INDEX ix_tenant_memberships_user_id ON tenant_memberships (user_id);
```

### Billing state (provider status vs internal access state)
```sql
CREATE TABLE tenant_subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES plans(id),
  provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
  provider_customer_id TEXT,
  provider_subscription_id TEXT,
  provider_status VARCHAR(50) NOT NULL,
  internal_access_state VARCHAR(50) NOT NULL CHECK (internal_access_state IN (
    'trialing','active','past_due_grace','past_due_locked','canceled',
    'chargeback_locked','unpaid_locked','incomplete_locked')),
  locked_reason TEXT,
  grace_ends_at TIMESTAMPTZ, trial_ends_at TIMESTAMPTZ,
  current_period_start TIMESTAMPTZ, current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
  canceled_at TIMESTAMPTZ, last_reconciled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_subscription_id)
);
CREATE INDEX ix_tenant_subscriptions_tenant_access ON tenant_subscriptions (tenant_id, internal_access_state);
```

### Contacts + suppression (survives re-import)
```sql
CREATE TABLE contacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email CITEXT, phone TEXT, first_name TEXT, last_name TEXT,
  company_name TEXT, title TEXT, website TEXT, linkedin_url TEXT,
  status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active','suppressed','unsubscribed','deleted')),
  source TEXT, tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
  CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
CREATE UNIQUE INDEX ux_contacts_tenant_email_active ON contacts (tenant_id, email)
  WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_contacts_tenant_status ON contacts (tenant_id, status);
CREATE INDEX ix_contacts_tenant_created_at ON contacts (tenant_id, created_at DESC);

CREATE TABLE suppression_entries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  email CITEXT, phone TEXT,
  channel VARCHAR(30) NOT NULL CHECK (channel IN ('email','sms','all')),
  reason VARCHAR(60) NOT NULL, source VARCHAR(60) NOT NULL,
  actor_user_id UUID REFERENCES users(id),
  reinstated_at TIMESTAMPTZ, reinstated_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (contact_id IS NOT NULL OR email IS NOT NULL OR phone IS NOT NULL)
);
CREATE UNIQUE INDEX ux_suppression_tenant_email_channel_active ON suppression_entries (tenant_id, email, channel)
  WHERE email IS NOT NULL AND reinstated_at IS NULL;
CREATE UNIQUE INDEX ux_suppression_tenant_phone_channel_active ON suppression_entries (tenant_id, phone, channel)
  WHERE phone IS NOT NULL AND reinstated_at IS NULL;
CREATE UNIQUE INDEX ux_suppression_tenant_contact_channel_active ON suppression_entries (tenant_id, contact_id, channel)
  WHERE contact_id IS NOT NULL AND reinstated_at IS NULL;
```

### Knowledge embeddings (global safety)
```sql
CREATE TABLE knowledge_embeddings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  source_table TEXT NOT NULL, source_id UUID NOT NULL, content_hash TEXT NOT NULL,
  embedding vector(1536) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_global BOOLEAN NOT NULL DEFAULT FALSE,
  approved_for_global BOOLEAN NOT NULL DEFAULT FALSE,
  pii_scrubbed BOOLEAN NOT NULL DEFAULT FALSE,
  approved_by_user_id UUID REFERENCES users(id), approved_at TIMESTAMPTZ, retained_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((tenant_id IS NOT NULL AND is_global = FALSE) OR (tenant_id IS NULL AND is_global = TRUE)),
  CHECK (is_global = FALSE OR (approved_for_global = TRUE AND pii_scrubbed = TRUE AND approved_at IS NOT NULL))
);
CREATE UNIQUE INDEX ux_knowledge_embeddings_source
ON knowledge_embeddings (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), source_table, source_id, content_hash);
CREATE INDEX ix_knowledge_embeddings_tenant_created_at ON knowledge_embeddings (tenant_id, created_at DESC);
```
> ivfflat/HNSW vector index only after enough rows exist. **Vector retrieval must still filter by tenant/global approval before returning content.** Embedding service contract → [AI_SAFETY_AND_GROUNDEDNESS](AI_SAFETY_AND_GROUNDEDNESS.md); retention → [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md).

### Send intent + outbound uniqueness (no duplicate sends)
```sql
CREATE TABLE send_intents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  campaign_id UUID NOT NULL REFERENCES outreach_campaigns(id) ON DELETE CASCADE,
  campaign_prospect_id UUID NOT NULL REFERENCES campaign_prospects(id) ON DELETE CASCADE,
  draft_id UUID REFERENCES outreach_drafts(id) ON DELETE SET NULL,
  sequence_step INTEGER NOT NULL DEFAULT 1,
  intent_key TEXT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','blocked','scheduled','leased','sent','failed','canceled')),
  scheduled_for TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, intent_key),
  UNIQUE (tenant_id, campaign_prospect_id, sequence_step)
);
CREATE INDEX ix_send_intents_tenant_status_scheduled ON send_intents (tenant_id, status, scheduled_for);

CREATE TABLE outbound_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  send_intent_id UUID NOT NULL REFERENCES send_intents(id) ON DELETE RESTRICT,
  provider VARCHAR(50) NOT NULL, provider_message_id TEXT, provider_idempotency_key TEXT,
  status VARCHAR(50) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','sending','sent','failed','bounced','replied','canceled')),
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (send_intent_id),
  UNIQUE (tenant_id, provider, provider_idempotency_key)
);
CREATE INDEX ix_outbound_messages_tenant_status_created ON outbound_messages (tenant_id, status, created_at DESC);
```

### Idempotency + audit immutability
```sql
CREATE TABLE idempotency_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  actor_user_id UUID REFERENCES users(id),
  key TEXT NOT NULL, request_hash TEXT NOT NULL, response_hash TEXT, status_code INTEGER,
  locked_until TIMESTAMPTZ, expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, key)
);
CREATE INDEX ix_idempotency_keys_expiry ON idempotency_keys (expires_at);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
  actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL, object_type TEXT, object_id UUID, request_id TEXT, job_id UUID,
  redacted_details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_events_tenant_created_at ON audit_events (tenant_id, created_at DESC);
CREATE INDEX ix_audit_events_object ON audit_events (tenant_id, object_type, object_id);
-- Enforce by role grants: app runtime role may INSERT/SELECT only. No UPDATE/DELETE. Add trigger guard if needed.
```

## 7. Required composite indexes (tenant-first)

| Table family | Index patterns |
|---|---|
| Tenant tables | `(tenant_id, id)`, `(tenant_id, status)`, `(tenant_id, created_at DESC)` |
| Contacts/prospects/leads | `(tenant_id, email)`, `(tenant_id, phone)`, `(tenant_id, status)`, `(tenant_id, research_status)` |
| Campaigns/drafts/reviews | `(tenant_id, campaign_id)`, `(tenant_id, status)`, `(tenant_id, created_at DESC)` |
| Jobs/workers | `(status, run_at)`, `(tenant_id, status, run_at)`, `(locked_until)`, `(dedupe_key)` |
| Send gate/sending | `(tenant_id, send_intent_id)`, `(tenant_id, campaign_prospect_id, sequence_step)`, `(tenant_id, status, scheduled_for)` |
| Webhooks/billing | `(provider, provider_event_id)`, `(tenant_id, created_at DESC)`, `(status, received_at)` |
| Audit/outcomes | `(tenant_id, created_at DESC)`, `(tenant_id, object_type, object_id)`, `(tenant_id, event_type, created_at DESC)` |

## 8. RLS pattern

```sql
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY contacts_tenant_isolation ON contacts
USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

- App/worker DB roles must **never** have `BYPASSRLS`.
- Platform-admin access uses explicit platform routes + audited support grants, **not** disabled RLS.
- Workers set the same tenant context as HTTP requests before touching tenant data.
- RLS is required but not enough — routes/services still check RBAC + object ownership (see [AUTH_AND_RBAC](AUTH_AND_RBAC.md)).

## 9. Database acceptance checklist

- [ ] Empty DB migration runs cleanly up/down (where rollback supported).
- [ ] Required extensions install in local and production-like environments.
- [ ] Every tenant-owned table has `tenant_id`, forced RLS, tenant-first indexes.
- [ ] Tenant A cannot read/update/delete/export/send-to/embed Tenant B data.
- [ ] API object authorization blocks IDOR even with guessed IDs.
- [ ] Duplicate imports are deduped, not silently duplicated.
- [ ] Duplicate send attempts return the existing send intent/outbound message.
- [ ] Billing locks block routes and workers at claim time.
- [ ] Suppression works after re-import by email/phone/contact.
- [ ] Global embeddings cannot be created unless approved, PII-scrubbed, tenant-null.
- [ ] Deletion/export purges or redacts contacts, prospect research, embeddings per policy.
- [ ] Audit logs cannot be updated/deleted by normal app roles.
- [ ] CI runs migration smoke, RLS isolation, object auth, duplicate-send, billing-lock, privacy-delete tests.
