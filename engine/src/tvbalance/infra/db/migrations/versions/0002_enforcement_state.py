"""Enforcement state per TV, so debounce, warnings and the power-off cap survive restarts.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enforcement_state",
        sa.Column("tv_id", sa.String(36), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tv_id"], ["tvs.id"], name="fk_enforcement_state_tv_id_tvs", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tv_id", name="pk_enforcement_state"),
    )


def downgrade() -> None:
    op.drop_table("enforcement_state")
