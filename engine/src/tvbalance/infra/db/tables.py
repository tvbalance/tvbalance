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

enforcement_state = Table(
    "enforcement_state",
    metadata,
    Column("tv_id", ForeignKey("tvs.id", ondelete="CASCADE"), primary_key=True),
    Column("state", JSON, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)

# One row, always id 1: the household has a single admin account.
admin = Table(
    "admin",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("password_hash", String, nullable=False),
    Column("pin_hash", String, nullable=True),
    Column("pin_failures", Integer, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("kind", String, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("last_seen_at", UtcDateTime, nullable=False),
    Column("expires_at", UtcDateTime, nullable=False),
    Column("user_agent", String, nullable=False),
)

api_tokens = Table(
    "api_tokens",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("scopes", JSON, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("last_used_at", UtcDateTime, nullable=True),
    Column("revoked_at", UtcDateTime, nullable=True),
)
