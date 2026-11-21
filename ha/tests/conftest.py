import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest

from tvbalance_client import Event, TVBalanceClient


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from ha/custom_components."""


class EventStream:
    """Stands in for the Engine's WebSocket: tests push events, drop the socket or fail it."""

    def __init__(self) -> None:
        self.items: asyncio.Queue[Event | Exception | None] = asyncio.Queue()
        self.connections = 0

    def push(self, type: str, tv_id: str | None = "tv1", **payload: Any) -> None:
        self.items.put_nowait(Event(type, tv_id, datetime.now(UTC), payload))

    def push_status(self, tv_id: str, status: dict[str, Any]) -> None:
        self.items.put_nowait(Event("status", tv_id, None, status))

    def drop(self) -> None:
        self.items.put_nowait(None)

    def fail(self, error: Exception) -> None:
        self.items.put_nowait(error)

    async def events(self, client: TVBalanceClient) -> AsyncIterator[Event]:
        self.connections += 1
        while True:
            item = await self.items.get()
            if item is None:
                return
            if isinstance(item, Exception):
                raise item
            yield item


@pytest.fixture(autouse=True)
def stream() -> Iterator[EventStream]:
    fake = EventStream()
    with patch.object(TVBalanceClient, "events", lambda self: fake.events(self)):
        yield fake
