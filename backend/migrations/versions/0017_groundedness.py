"""add groundedness to safety gate types

Revision ID: 00017_groundedness
Revises: 00016_safety
Create Date: 2026-06-23 00:00:17

"""

from alembic import op

revision = "00017_groundedness"
down_revision = "00016_safety"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_safety_gate_results_gate_type",
        "safety_gate_results",
        type_="check",
    )
    op.create_check_constraint(
        "ck_safety_gate_results_gate_type",
        "safety_gate_results",
        "gate_type IN ('prompt_injection', 'source_trust', 'groundedness')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_safety_gate_results_gate_type",
        "safety_gate_results",
        type_="check",
    )
    op.create_check_constraint(
        "ck_safety_gate_results_gate_type",
        "safety_gate_results",
        "gate_type IN ('prompt_injection', 'source_trust')",
    )
