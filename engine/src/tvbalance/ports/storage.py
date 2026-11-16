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


class EnforcementStateStore(Protocol):
    async def load(self, tv_id: str) -> EnforcementState:
        """A TV without saved state, or with an unreadable one, starts from a fresh state."""
        ...

    async def save(self, tv_id: str, state: EnforcementState) -> None: ...


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
    def enforcement(self) -> EnforcementStateStore: ...

    async def close(self) -> None: ...
