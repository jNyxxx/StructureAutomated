"""jobs: durable queue/outbox (Postgres source of truth) + forced RLS

Revision ID: 0006_jobs
Revises: 0005_idempotency_keys
Create Date: 2026-06-22 00:00:05

Tenant-owned (tenant_id NOT NULL) with forced RLS. The tenant clause isolates
normal access; the worker-context clause lets the worker claim jobs across
tenants (it sets app.worker_context='on' transaction-locally during the claim,
then processes each job under its own tenant context). Statuses follow
DATABASE_SCHEMA.md. last_error stores a safe value (exception type only) and the
payload must never carry raw secrets (CLAUDE.md rule 14).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_jobs"
down_revision = "0005_idempotency_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.Text, nullable=False),
        sa.Column(
            "payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'queued'")),
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column(
            "run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_jobs_tenant_idempotency_key"
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'leased', 'running', 'succeeded', "
            "'failed', 'dead_letter', 'canceled')",
            name="ck_jobs_status",
        ),
    )
    op.create_index("ix_jobs_status_run_after", "jobs", ["status", "run_after"])
    op.create_index("ix_jobs_tenant_status_run_after", "jobs", ["tenant_id", "status", "run_after"])
    op.create_index("ix_jobs_locked_until", "jobs", ["locked_until"])

    # Forced RLS. Tenant requests see only their own jobs; the worker claim path
    # (app.worker_context='on') sees all jobs to lease them. Static literal — no
    # interpolation; table/columns are developer-controlled.
    op.execute("ALTER TABLE jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY jobs_tenant_isolation ON jobs USING ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR current_setting('app.worker_context', true) = 'on'"
        ") WITH CHECK ("
        "tenant_id = current_setting('app.current_tenant_id', true)::uuid "
        "OR current_setting('app.worker_context', true) = 'on'"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS jobs_tenant_isolation ON jobs")
    op.drop_index("ix_jobs_locked_until", table_name="jobs")
    op.drop_index("ix_jobs_tenant_status_run_after", table_name="jobs")
    op.drop_index("ix_jobs_status_run_after", table_name="jobs")
    op.drop_table("jobs")
