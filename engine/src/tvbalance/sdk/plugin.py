"""What an adapter package exports through the `tvbalance.adapters` entry point."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from tvbalance.ports.tv import TVAdapter
from tvbalance.sdk.types import AdapterConfig, AdapterInfo, DiscoveredDevice

AdapterFactory = Callable[[AdapterConfig], TVAdapter]
Discoverer = Callable[[], Awaitable[list[DiscoveredDevice]]]


@dataclass(frozen=True, slots=True)
class AdapterPlugin:
    info: AdapterInfo
    factory: AdapterFactory
    discover: Discoverer | None = None
