"""Ports for the engine's other collaborators. Implementations arrive with later modules."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class EventPublisher(Protocol):
    async def publish(self, event_type: str, payload: dict[str, object]) -> None: ...


class Notifier(Protocol):
    async def notify(self, title: str, message: str) -> None: ...


class Entitlements(Protocol):
    """Single Free/Pro decision point. Verification is open; Pro features are a separate package."""

    def is_pro(self) -> bool: ...

    def max_tvs(self) -> int: ...


class EPGSource(Protocol):
    async def title_at(self, channel_id: str, when: datetime) -> str | None: ...
