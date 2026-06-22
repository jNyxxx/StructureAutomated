"""Reusable forced row-level-security convention.

Every tenant-owned table (created from Slice 7 on) must enable AND force RLS and
carry a tenant-isolation policy keyed on the transaction-local
``app.current_tenant_id``. Statements are built here so migrations stay uniform.

Table names are developer-controlled identifiers (never request input), so the
interpolation below is safe; ``# noqa: S608`` documents that intent.
"""

from __future__ import annotations

_TENANT_PREDICATE = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"


def forced_rls_statements(table: str) -> list[str]:
    """SQL to enable + force RLS and add the tenant-isolation policy for ``table``."""
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",  # noqa: S608
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",  # noqa: S608
        (
            f"CREATE POLICY {table}_tenant_isolation ON {table} "  # noqa: S608
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        ),
    ]


def apply_forced_rls(table: str) -> None:
    """Execute the forced-RLS statements via the active Alembic operation."""
    from alembic import op

    for statement in forced_rls_statements(table):
        op.execute(statement)
