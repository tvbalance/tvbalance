"""Ports for durable state. The SQLite implementations live in ``tvbalance.infra.db``."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from tvbalance.domain.enforcement import EnforcementState
from tvbalance.domain.models import Override, Policy, Usage


class NotFoundError(LookupError):
    """The record does not exist (or was removed meanwhile)."""


@dataclass(frozen=True, slots=True)
class TvRecord:
    id: str
    adapter_id: str
    name: str
    host: str
    credentials: dict[str, str] = field(repr=False)
    policy_id: int | None
    enabled: bool
    created_at: datetime
    needs_pairing: bool = False  # the stored credentials cannot be read: pair again


@dataclass(frozen=True, slots=True)
class PolicyRecord:
    id: int
    name: str
    policy: Policy
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredEvent:
    id: int
    tv_id: str | None
    occurred_at: datetime
    type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AdminRecord:
    password_hash: str = field(repr=False)
    pin_hash: str | None = field(repr=False)
    pin_failures: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: str
    kind: str  # "admin" or "pin"
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    user_agent: str


@dataclass(frozen=True, slots=True)
class ApiTokenRecord:
    id: str
    name: str
    scopes: frozenset[str]
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class PushSubscriptionRecord:
    id: str
    endpoint: str
    p256dh: str
    auth: str
    events: frozenset[str]
    language: str
    app_url: str
    user_agent: str
    created_at: datetime
    last_sent_at: datetime | None
    failures: int


class TvStore(Protocol):
    async def add(
        self,
        adapter_id: str,
        name: str,
        host: str,
        credentials: dict[str, str],
        policy_id: int | None = None,
    ) -> TvRecord: ...

    async def get(self, tv_id: str) -> TvRecord | None: ...

    async def list(self) -> list[TvRecord]: ...

    async def update_credentials(self, tv_id: str, credentials: dict[str, str]) -> None: ...

    async def assign_policy(self, tv_id: str, policy_id: int | None) -> None: ...

    async def set_enabled(self, tv_id: str, enabled: bool) -> None: ...

    async def rename(self, tv_id: str, name: str) -> None: ...

    async def remove(self, tv_id: str) -> bool:
        """Delete the TV with its usage and overrides; events are kept without the link."""
        ...


class PolicyStore(Protocol):
    async def create(self, name: str, policy: Policy) -> int: ...

    async def get(self, policy_id: int) -> PolicyRecord | None: ...

    async def save(self, policy_id: int, policy: Policy, name: str | None = None) -> None: ...

    async def list(self) -> list[PolicyRecord]: ...


class UsageStore(Protocol):
    async def get(self, tv_id: str, day: date) -> Usage:
        """Nothing is stored for a day without viewing: the result is all zeros."""
        ...

    async def add_watched(self, tv_id: str, day: date, seconds: int) -> None:
        """Atomic: concurrent calls never lose an increment."""
        ...

    async def add_bonus(self, tv_id: str, day: date, minutes: int) -> None: ...


class OverrideStore(Protocol):
    async def add(self, tv_id: str, override: Override) -> None: ...

    async def active(self, tv_id: str, now: datetime) -> tuple[Override, ...]:
        """Overrides not yet expired at ``now``, oldest first (``evaluate`` picks the winner)."""
        ...

    async def clear(self, tv_id: str) -> int: ...


class EventLog(Protocol):
    async def append(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None: ...

    async def recent(
        self, tv_id: str | None, since: datetime, limit: int = 100
    ) -> list[StoredEvent]:
        """Newest first. ``tv_id=None`` means every TV, including events without one."""
        ...


class SettingsStore(Protocol):
    async def get(self, key: str, default: Any = None) -> Any: ...

    async def set(self, key: str, value: Any) -> None: ...


class SecretSettingsStore(Protocol):
    """Small text secrets (for example a token handed to another system), sealed at rest."""

    async def get(self, key: str) -> str | None:
        """A missing or unreadable secret is None."""
        ...

    async def set(self, key: str, value: str) -> None: ...


class PushSubscriptionStore(Protocol):
    """Browser Web Push subscriptions. The auth secret is sealed at rest."""

    async def upsert(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        events: frozenset[str],
        language: str,
        app_url: str,
        user_agent: str,
    ) -> tuple[PushSubscriptionRecord, bool]:
        """Create the subscription, or refresh the one with the same endpoint. True when created."""
        ...

    async def list(self) -> list[PushSubscriptionRecord]: ...

    async def get(self, subscription_id: str) -> PushSubscriptionRecord | None: ...

    async def update_events(self, subscription_id: str, events: frozenset[str]) -> bool: ...

    async def delete(self, subscription_id: str) -> bool: ...

    async def record_delivery(self, subscription_id: str) -> None:
        """Stamp the last send time and clear the failure count."""
        ...

    async def record_failure(self, subscription_id: str) -> int:
        """Count one more consecutive failure and return the total (0 for an unknown id)."""
        ...


class EnforcementStateStore(Protocol):
    async def load(self, tv_id: str) -> EnforcementState:
        """A TV without saved state, or with an unreadable one, starts from a fresh state."""
        ...

    async def save(self, tv_id: str, state: EnforcementState) -> None: ...


class AuthStore(Protocol):
    """The admin account, its sessions and API tokens. Only hashes of secrets are stored."""

    async def get_admin(self) -> AdminRecord | None: ...

    async def create_admin(self, password_hash: str) -> bool:
        """False when an admin already exists."""
        ...

    async def set_password_hash(self, password_hash: str) -> None: ...

    async def set_pin_hash(self, pin_hash: str | None) -> None:
        """Setting or removing the PIN also clears the failure counter."""
        ...

    async def record_pin_failure(self) -> int:
        """Returns the number of consecutive failures including this one."""
        ...

    async def reset_pin_failures(self) -> None: ...

    async def add_session(
        self, token_hash: str, kind: str, expires_at: datetime, user_agent: str
    ) -> SessionRecord: ...

    async def get_session(self, token_hash: str) -> SessionRecord | None:
        """Expiry is not checked here: the caller compares ``expires_at`` with its clock."""
        ...

    async def touch_session(
        self, session_id: str, last_seen_at: datetime, expires_at: datetime
    ) -> None: ...

    async def list_sessions(self) -> list[SessionRecord]:
        """Oldest first."""
        ...

    async def revoke_session(self, session_id: str) -> bool: ...

    async def revoke_all_sessions(self, except_id: str | None = None) -> int: ...

    async def purge_expired_sessions(self, now: datetime) -> int: ...

    async def add_token(
        self, name: str, token_hash: str, scopes: frozenset[str]
    ) -> ApiTokenRecord: ...

    async def get_token(self, token_hash: str) -> ApiTokenRecord | None:
        """A revoked token is not found."""
        ...

    async def touch_token(self, token_id: str, used_at: datetime) -> None: ...

    async def list_tokens(self) -> list[ApiTokenRecord]:
        """Oldest first, revoked tokens included."""
        ...

    async def revoke_token(self, token_id: str) -> bool: ...


class Storage(Protocol):
    """The stores are read-only attributes, so implementations may narrow their types."""

    @property
    def tvs(self) -> TvStore: ...

    @property
    def policies(self) -> PolicyStore: ...

    @property
    def usage(self) -> UsageStore: ...

    @property
    def overrides(self) -> OverrideStore: ...

    @property
    def events(self) -> EventLog: ...

    @property
    def settings(self) -> SettingsStore: ...

    @property
    def secrets(self) -> SecretSettingsStore: ...

    @property
    def enforcement(self) -> EnforcementStateStore: ...

    @property
    def auth(self) -> AuthStore: ...

    @property
    def push(self) -> PushSubscriptionStore: ...

    async def close(self) -> None: ...
