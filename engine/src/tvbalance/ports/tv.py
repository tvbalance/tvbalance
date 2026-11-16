"""The port every TV adapter implements."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from tvbalance.domain.models import Action, Observation
from tvbalance.sdk.types import AppInfo, ChannelInfo, InputInfo, PairingState


class PairingFlow(Protocol):
    """State machine for pairing: start, wait for the user, then complete or fail."""

    async def start(self) -> PairingState: ...

    async def poll(self) -> PairingState: ...

    def credentials(self) -> dict[str, str]:
        """Credentials to persist once the state is COMPLETED."""
        ...


class TVAdapter(Protocol):
    """Adapters never apply their own timeouts: the engine wraps every call (TVSession)."""

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def observe(self) -> Observation: ...

    async def execute(self, action: Action) -> None: ...

    async def list_apps(self) -> list[AppInfo]: ...

    async def list_inputs(self) -> list[InputInfo]: ...

    async def list_channels(self) -> list[ChannelInfo]: ...

    def pairing(self) -> PairingFlow: ...


class SupportsPush(Protocol):
    """Optional: adapters declaring Capability.PUSH_UPDATES notify when the TV state changes."""

    def on_change(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register ``callback``; returns a function that unregisters it."""
        ...
