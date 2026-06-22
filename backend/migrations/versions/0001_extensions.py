"""create required postgresql extensions

Revision ID: 0001_extensions
Revises:
Create Date: 2026-06-22 00:00:00

Creates only the required PostgreSQL extensions. Idempotent via
CREATE EXTENSION IF NOT EXISTS. No tables, roles, or RLS policies (later slices).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_extensions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS citext")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
