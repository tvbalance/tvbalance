"""TVSession: the only way the engine talks to a TV.

Every adapter call gets a hard timeout and every unexpected failure is mapped to a typed
error, so a hung or buggy adapter can never freeze supervision. (A prototype wedged in a
ghost "online" state because a send to a dead peer never returned.)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass

from tvbalance.domain.models import Action, Observation
from tvbalance.ports.tv import TVAdapter
from tvbalance.sdk.errors import TVError, TVTimeoutError
from tvbalance.sdk.types import AppInfo, ChannelInfo, InputInfo


@dataclass(frozen=True, slots=True)
class SessionTimeouts:
    connect: float = 120.0
    observe: float = 30.0
    execute: float = 30.0
    inventory: float = 30.0


class TVSession:
    def __init__(self, adapter: TVAdapter, timeouts: SessionTimeouts | None = None) -> None:
        self._adapter = adapter
        self._timeouts = timeouts or SessionTimeouts()

    async def _bounded[T](self, what: str, call: Awaitable[T], limit: float) -> T:
        try:
            async with asyncio.timeout(limit):
                return await call
        except TimeoutError as ex:
            raise TVTimeoutError(f"{what} timed out after {limit:g}s") from ex
        except TVError:
            raise
        except Exception as ex:
            raise TVError(f"{what} failed: {type(ex).__name__}: {ex}") from ex

    async def connect(self) -> None:
        await self._bounded("connect", self._adapter.connect(), self._timeouts.connect)

    async def close(self) -> None:
        await self._bounded("close", self._adapter.close(), self._timeouts.execute)

    async def observe(self) -> Observation:
        return await self._bounded("observe", self._adapter.observe(), self._timeouts.observe)

    async def execute(self, action: Action) -> None:
        await self._bounded("execute", self._adapter.execute(action), self._timeouts.execute)

    async def list_apps(self) -> list[AppInfo]:
        return await self._bounded("list_apps", self._adapter.list_apps(), self._timeouts.inventory)

    async def list_inputs(self) -> list[InputInfo]:
        return await self._bounded(
            "list_inputs", self._adapter.list_inputs(), self._timeouts.inventory
        )

    async def list_channels(self) -> list[ChannelInfo]:
        return await self._bounded(
            "list_channels", self._adapter.list_channels(), self._timeouts.inventory
        )
