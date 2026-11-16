"""Engine events: domain events as stored records, and the bus that delivers them."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum
from typing import Any

from tvbalance.domain.models import (
    Action,
    Blocked,
    DomainEvent,
    EnforcementPaused,
    EnforcementUnavailable,
    PoweredOff,
    Redirected,
    TimeWarning,
)
from tvbalance.ports.storage import EventLog

log = logging.getLogger(__name__)

QUEUE_SIZE = 100


@dataclass(frozen=True, slots=True)
class BusEvent:
    tv_id: str | None
    type: str
    payload: dict[str, Any]
    at: datetime


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _action_payload(action: Action) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": _snake(type(action).__name__)}
    for field in fields(action):
        value = getattr(action, field.name)
        payload.setdefault(field.name, value.value if isinstance(value, StrEnum) else value)
    return payload


def to_record(event: DomainEvent) -> tuple[str, dict[str, Any]]:
    """The stored type and JSON payload of a domain event."""
    match event:
        case TimeWarning(minutes_left, limit):
            return "time_warning", {"minutes_left": minutes_left, "limit": limit.value}
        case Blocked(reason):
            return "blocked", {"reason": reason.value}
        case Redirected(action):
            return "redirected", {"action": _action_payload(action)}
        case PoweredOff():
            return "powered_off", {}
        case EnforcementPaused(until):
            return "enforcement_paused", {"until": until.isoformat()}
        case EnforcementUnavailable(reason):
            return "enforcement_unavailable", {"reason": reason.value}


class EventBus:
    """Stores every event in the log, then hands it to the live subscribers.

    A slow subscriber loses its oldest events; publishing never waits for anyone.
    """

    def __init__(self, event_log: EventLog, queue_size: int = QUEUE_SIZE) -> None:
        self._log = event_log
        self._queue_size = queue_size
        self._queues: list[asyncio.Queue[BusEvent]] = []

    async def publish(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None:
        try:
            await self._log.append(tv_id, event_type, payload, at)
        except Exception:
            log.exception("could not store the %s event", event_type)
        event = BusEvent(tv_id, event_type, payload, at)
        for queue in self._queues:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[BusEvent]]:
        queue: asyncio.Queue[BusEvent] = asyncio.Queue(self._queue_size)
        self._queues.append(queue)
        try:
            yield queue
        finally:
            self._queues.remove(queue)
