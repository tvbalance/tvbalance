"""Profile activations and the profile calendar.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_activations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("excluded_tv_ids", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["policies.id"],
            name="fk_profile_activations_policy_id_policies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profile_activations"),
    )
    op.create_index("ix_profile_activations_ends_at", "profile_activations", ["ends_at"])
    op.create_table(
        "calendar_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=True),
        sa.Column("start_time", sa.String(), nullable=True),
        sa.Column("end_time", sa.String(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("excluded_tv_ids", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["policies.id"],
            name="fk_calendar_entries_policy_id_policies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_calendar_entries"),
    )


def downgrade() -> None:
    op.drop_table("calendar_entries")
    op.drop_index("ix_profile_activations_ends_at", table_name="profile_activations")
    op.drop_table("profile_activations")
