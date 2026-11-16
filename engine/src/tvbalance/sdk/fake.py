"""In-memory TV used by tests and as the reference adapter for the contract suite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from tvbalance.domain.models import Action, Observation, Power
from tvbalance.ports.tv import PairingFlow, TVAdapter
from tvbalance.sdk.errors import TVError
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import (
    AdapterConfig,
    AdapterInfo,
    AppInfo,
    Capability,
    ChannelInfo,
    DiscoveredDevice,
    InputInfo,
    Maturity,
    PairingState,
)


class FakePairing:
    """Completes after one user confirmation (the first poll)."""

    def __init__(self) -> None:
        self._state = PairingState.IDLE

    async def start(self) -> PairingState:
        self._state = PairingState.WAITING_FOR_USER
        return self._state

    async def poll(self) -> PairingState:
        if self._state is PairingState.WAITING_FOR_USER:
            self._state = PairingState.COMPLETED
        return self._state

    def credentials(self) -> dict[str, str]:
        return {"client_key": "fake-key"} if self._state is PairingState.COMPLETED else {}


@dataclass
class FakeTV:
    host: str = "fake.local"
    observation: Observation = field(
        default_factory=lambda: Observation(observed_at=datetime.now(UTC), power=Power.ON)
    )
    apps: list[AppInfo] = field(default_factory=lambda: [AppInfo("video", "Video")])
    inputs: list[InputInfo] = field(default_factory=lambda: [InputInfo("hdmi1", "HDMI 1")])
    channels: list[ChannelInfo] = field(default_factory=lambda: [ChannelInfo("c1", "One", "1")])
    executed: list[Action] = field(default_factory=list)
    connected: bool = False
    hang_observe: bool = False
    fail_execute: bool = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def observe(self) -> Observation:
        if self.hang_observe:
            await asyncio.Event().wait()
        if not self.connected:
            raise TVError("not connected")
        return self.observation

    async def execute(self, action: Action) -> None:
        if self.fail_execute:
            raise TVError("command failed")
        self.executed.append(action)

    async def list_apps(self) -> list[AppInfo]:
        return list(self.apps)

    async def list_inputs(self) -> list[InputInfo]:
        return list(self.inputs)

    async def list_channels(self) -> list[ChannelInfo]:
        return list(self.channels)

    def pairing(self) -> PairingFlow:
        return FakePairing()


_SIMULATED: dict[str, FakeTV] = {}


def _factory(config: AdapterConfig) -> TVAdapter:
    return _SIMULATED.get(config.host) or FakeTV(host=config.host)


class FakeHarness:
    """Contract-suite harness: the TV the factory returns for ``config.host``."""

    def __init__(self) -> None:
        self.tv = FakeTV(host="harness.fake")
        self.config = AdapterConfig(host=self.tv.host, credentials={})

    async def set_power(self, power: Power) -> None:
        self.tv.observation = Observation(observed_at=datetime.now(UTC), power=power)

    async def drop_connection(self) -> None:
        self.tv.connected = False


@asynccontextmanager
async def _harness() -> AsyncIterator[FakeHarness]:
    harness = FakeHarness()
    _SIMULATED[harness.tv.host] = harness.tv
    try:
        yield harness
    finally:
        _SIMULATED.pop(harness.tv.host, None)


async def _discover() -> list[DiscoveredDevice]:
    return [DiscoveredDevice(adapter_id="fake", host="fake.local", name="Fake TV")]


PLUGIN = AdapterPlugin(
    info=AdapterInfo(
        id="fake",
        brand="Fake",
        display_name="Fake TV (testing)",
        maturity=Maturity.EXPERIMENTAL,
        capabilities=frozenset(Capability),
        testing_only=True,
    ),
    factory=_factory,
    discover=_discover,
)
