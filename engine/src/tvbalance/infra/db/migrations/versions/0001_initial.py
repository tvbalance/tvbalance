"""Initial schema: policies, TVs, usage, overrides, events, settings.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_policies"),
    )
    op.create_table(
        "tvs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("adapter_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("host", sa.String(), nullable=False),
        sa.Column("credentials_enc", sa.LargeBinary(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["policies.id"], name="fk_tvs_policy_id_policies", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tvs"),
    )
    op.create_table(
        "usage",
        sa.Column("tv_id", sa.String(36), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("watched_seconds", sa.Integer(), nullable=False),
        sa.Column("bonus_minutes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tv_id"], ["tvs.id"], name="fk_usage_tv_id_tvs", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tv_id", "day", name="pk_usage"),
    )
    op.create_table(
        "overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tv_id", sa.String(36), nullable=False),
        sa.Column("allow", sa.Boolean(), nullable=False),
        sa.Column("until", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tv_id"], ["tvs.id"], name="fk_overrides_tv_id_tvs", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_overrides"),
    )
    op.create_index("ix_overrides_tv_id_until", "overrides", ["tv_id", "until"])
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tv_id", sa.String(36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tv_id"], ["tvs.id"], name="fk_events_tv_id_tvs", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"])
    op.create_table(
        "settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_settings"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_index("ix_events_occurred_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_overrides_tv_id_until", table_name="overrides")
    op.drop_table("overrides")
    op.drop_table("usage")
    op.drop_table("tvs")
    op.drop_table("policies")
