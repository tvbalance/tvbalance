"""Finding TVs on the network and pairing them with the engine."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from tvbalance.ports.storage import Storage
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import DiscoveredDevice

log = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 6.0  # seconds an adapter may spend searching


@dataclass(frozen=True, slots=True)
class FoundTv:
    adapter_id: str
    adapter_name: str
    host: str
    name: str
    model: str | None
    already_added: bool


class PairingService:
    def __init__(
        self,
        storage: Storage,
        plugins: dict[str, AdapterPlugin],
        include_testing: bool = False,
        discovery_timeout: float = DISCOVERY_TIMEOUT,
    ) -> None:
        self._storage = storage
        self._plugins = plugins
        self._include_testing = include_testing
        self._discovery_timeout = discovery_timeout
        self._scan: asyncio.Task[list[DiscoveredDevice]] | None = None

    async def discover(self) -> list[FoundTv]:
        """TVs every installed adapter can see, once per adapter and address.

        Searches that overlap share one scan, so a second browser tab does not send a second
        burst of multicast.
        """
        if self._scan is None or self._scan.done():
            self._scan = asyncio.create_task(self._search())
        devices = await asyncio.shield(self._scan)
        added = {(r.adapter_id, r.host.lower()) for r in await self._storage.tvs.list()}
        return [
            FoundTv(
                d.adapter_id,
                self._plugins[d.adapter_id].info.display_name,
                d.host,
                d.name,
                d.model,
                (d.adapter_id, d.host.lower()) in added,
            )
            for d in devices
        ]

    async def _search(self) -> list[DiscoveredDevice]:
        searchable = [
            plugin
            for _, plugin in sorted(self._plugins.items())
            if plugin.discover is not None
            and (self._include_testing or not plugin.info.testing_only)
        ]
        results = await asyncio.gather(*(self._ask(plugin) for plugin in searchable))
        found: dict[tuple[str, str], DiscoveredDevice] = {}
        for devices in results:
            for device in devices:
                found.setdefault((device.adapter_id, device.host.lower()), device)
        return list(found.values())

    async def _ask(self, plugin: AdapterPlugin) -> list[DiscoveredDevice]:
        assert plugin.discover is not None
        try:
            async with asyncio.timeout(self._discovery_timeout):
                devices = await plugin.discover()
        except Exception:
            log.warning("discovery by adapter %r failed", plugin.info.id, exc_info=True)
            return []
        return [d for d in devices if d.adapter_id == plugin.info.id]
