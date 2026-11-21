"""Finding TVs on the network and pairing them with the engine."""

from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from tvbalance.app.events import EventBus
from tvbalance.app.supervisor import Supervisor
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import Storage
from tvbalance.ports.tv import PairingFlow
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import AdapterConfig, DiscoveredDevice, PairingState

log = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 6.0  # seconds an adapter may spend searching
POLL_INTERVAL = 0.5  # seconds between two looks at a pairing flow
PAIRING_WINDOW = timedelta(minutes=3)  # how long a person has to accept on the TV
KEEP_FINISHED = timedelta(minutes=10)  # how long a finished pairing can still be read


class PairingError(Exception):
    code = "pairing_error"


class UnknownAdapter(PairingError):
    code = "not_found"


class UnknownPairing(PairingError):
    code = "not_found"


class AlreadyAdded(PairingError):
    code = "tv_exists"


class SessionState(StrEnum):
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class FoundTv:
    adapter_id: str
    adapter_name: str
    host: str
    name: str
    model: str | None
    already_added: bool


@dataclass(slots=True)
class PairingSession:
    id: str
    adapter_id: str
    host: str
    name: str
    expires_at: datetime
    flow: PairingFlow | None = None
    tv_id: str | None = None
    state: SessionState = SessionState.WAITING_FOR_USER
    finished_at: datetime | None = None
    task: asyncio.Task[None] | None = None


class PairingService:
    def __init__(
        self,
        storage: Storage,
        plugins: dict[str, AdapterPlugin],
        supervisor: Supervisor,
        bus: EventBus,
        clock: Clock,
        include_testing: bool = False,
        discovery_timeout: float = DISCOVERY_TIMEOUT,
        poll_interval: float = POLL_INTERVAL,
    ) -> None:
        self._storage = storage
        self._plugins = plugins
        self._supervisor = supervisor
        self._bus = bus
        self._clock = clock
        self._include_testing = include_testing
        self._discovery_timeout = discovery_timeout
        self._poll_interval = poll_interval
        self._scan: asyncio.Task[list[DiscoveredDevice]] | None = None
        self._sessions: dict[str, PairingSession] = {}

    # -- discovery --------------------------------------------------------------------------

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

    # -- pairing ----------------------------------------------------------------------------

    async def start(self, adapter_id: str, host: str, name: str | None = None) -> PairingSession:
        """Begin pairing a new TV; a pairing already waiting on this address is returned as is."""
        self._prune()
        plugin = self._plugins.get(adapter_id)
        if plugin is None:
            raise UnknownAdapter(f"adapter {adapter_id!r} is not installed")
        key = host.lower()
        for session in self._sessions.values():
            if session.state is SessionState.WAITING_FOR_USER and (
                session.adapter_id,
                session.host.lower(),
            ) == (adapter_id, key):
                return session
        for record in await self._storage.tvs.list():
            if (record.adapter_id, record.host.lower()) == (adapter_id, key):
                raise AlreadyAdded("this TV is already added")
        session = PairingSession(
            id=secrets.token_urlsafe(12),
            adapter_id=adapter_id,
            host=host,
            name=name or plugin.info.display_name,
            expires_at=self._clock.now() + PAIRING_WINDOW,
        )
        self._sessions[session.id] = session
        try:
            session.flow = plugin.factory(AdapterConfig(host, {})).pairing()
            await session.flow.start()
        except Exception:
            log.warning("pairing with %s could not start", host, exc_info=True)
            self._finish(session, SessionState.FAILED)
        else:
            session.task = asyncio.create_task(self._run(session), name=f"pairing-{session.id}")
        return session

    def get(self, pairing_id: str) -> PairingSession:
        self._prune()
        session = self._sessions.get(pairing_id)
        if session is None:
            raise UnknownPairing("pairing not found")
        return session

    async def stop(self) -> None:
        tasks = [s.task for s in self._sessions.values() if s.task is not None]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError, Exception):
                await task
        self._sessions.clear()

    async def _run(self, session: PairingSession) -> None:
        assert session.flow is not None
        try:
            while True:
                state = await session.flow.poll()
                if state is PairingState.COMPLETED:
                    await self._complete(session)
                    return
                if state is PairingState.FAILED:
                    self._finish(session, SessionState.FAILED)
                    return
                if self._clock.now() >= session.expires_at:
                    self._finish(session, SessionState.EXPIRED)
                    return
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("pairing with %s failed", session.host)
            self._finish(session, SessionState.FAILED)

    async def _complete(self, session: PairingSession) -> None:
        assert session.flow is not None
        record = await self._storage.tvs.add(
            session.adapter_id, session.name, session.host, session.flow.credentials()
        )
        session.tv_id = record.id
        await self._supervisor.refresh(record.id)
        await self._bus.publish(
            record.id,
            "tv_added",
            {"name": record.name, "adapter_id": record.adapter_id},
            self._clock.now(),
        )
        self._finish(session, SessionState.COMPLETED)

    def _finish(self, session: PairingSession, state: SessionState) -> None:
        session.state = state
        session.finished_at = self._clock.now()

    def _prune(self) -> None:
        cutoff = self._clock.now() - KEEP_FINISHED
        for pairing_id in [
            s.id for s in self._sessions.values() if s.finished_at and s.finished_at < cutoff
        ]:
            del self._sessions[pairing_id]
