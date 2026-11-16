"""Simulated TVs that let the contract suite drive any adapter without hardware."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from importlib.metadata import entry_points
from typing import Protocol

from tvbalance.domain.models import Power
from tvbalance.sdk.types import AdapterConfig

ENTRY_POINT_GROUP = "tvbalance.adapter_harnesses"


class SimulatedTV(Protocol):
    """A running fake TV plus the knobs the contract tests need."""

    config: AdapterConfig

    async def set_power(self, power: Power) -> None: ...

    async def drop_connection(self) -> None:
        """Abruptly lose the connection the adapter holds."""
        ...


type Harness = AbstractAsyncContextManager[SimulatedTV]


def load_harnesses() -> dict[str, Callable[[], Harness]]:
    """Harness factories keyed by adapter id (each call returns an async context manager)."""
    return {ep.name: ep.load() for ep in entry_points(group=ENTRY_POINT_GROUP)}
