"""Seconds viewed per app, input or channel and day.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_usage",
        sa.Column("tv_id", sa.String(36), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("content_id", sa.String(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tv_id"], ["tvs.id"], name="fk_content_usage_tv_id_tvs", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tv_id", "day", "kind", "content_id", name="pk_content_usage"),
    )


def downgrade() -> None:
    op.drop_table("content_usage")
