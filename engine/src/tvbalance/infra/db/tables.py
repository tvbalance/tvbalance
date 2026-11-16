"""Table definitions (SQLAlchemy Core: the domain uses frozen dataclasses, not mapped classes).

Keep in step with the migrations: a test fails when the two disagree.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
)

from tvbalance.infra.db.types import UtcDateTime

metadata = MetaData(
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
    }
)

policies = Table(
    "policies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("document", JSON, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)

tvs = Table(
    "tvs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("adapter_id", String, nullable=False),
    Column("name", String, nullable=False),
    Column("host", String, nullable=False),
    Column("credentials_enc", LargeBinary, nullable=False),
    Column("policy_id", ForeignKey("policies.id", ondelete="SET NULL"), nullable=True),
    Column("enabled", Boolean, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
)

usage = Table(
    "usage",
    metadata,
    Column("tv_id", ForeignKey("tvs.id", ondelete="CASCADE"), primary_key=True),
    Column("day", Date, primary_key=True),
    Column("watched_seconds", Integer, nullable=False),
    Column("bonus_minutes", Integer, nullable=False),
)

overrides = Table(
    "overrides",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tv_id", ForeignKey("tvs.id", ondelete="CASCADE"), nullable=False),
    Column("allow", Boolean, nullable=False),
    Column("until", UtcDateTime, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Index("ix_overrides_tv_id_until", "tv_id", "until"),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tv_id", ForeignKey("tvs.id", ondelete="SET NULL"), nullable=True),
    Column("occurred_at", UtcDateTime, nullable=False),
    Column("type", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Index("ix_events_occurred_at", "occurred_at"),
)

settings = Table(
    "settings",
    metadata,
    Column("key", String, primary_key=True),
    Column("value", JSON, nullable=False),
)
