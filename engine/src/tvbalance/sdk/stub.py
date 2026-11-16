"""Base for adapters that are declared but not implemented yet."""

from __future__ import annotations

from tvbalance.domain.models import Action, Observation
from tvbalance.ports.tv import PairingFlow
from tvbalance.sdk.types import AdapterConfig, AppInfo, ChannelInfo, InputInfo


class StubAdapter:
    """Every call raises NotImplementedError. Replace per brand as its module lands."""

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    async def connect(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def observe(self) -> Observation:
        raise NotImplementedError

    async def execute(self, action: Action) -> None:
        raise NotImplementedError

    async def list_apps(self) -> list[AppInfo]:
        raise NotImplementedError

    async def list_inputs(self) -> list[InputInfo]:
        raise NotImplementedError

    async def list_channels(self) -> list[ChannelInfo]:
        raise NotImplementedError

    def pairing(self) -> PairingFlow:
        raise NotImplementedError
