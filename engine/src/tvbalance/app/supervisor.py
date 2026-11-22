"""Supervisor: one TvWorker task per enabled TV whose adapter is installed."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from tvbalance.app.events import EventBus
from tvbalance.app.profiles import ProfileService
from tvbalance.app.status import Inventory, SupervisorSettings, TvStatus
from tvbalance.app.worker import TvWorker
from tvbalance.ports.services import Clock, Entitlements
from tvbalance.ports.storage import Storage, TvRecord
from tvbalance.sdk.plugin import AdapterPlugin

log = logging.getLogger(__name__)


class Supervisor:
    def __init__(
        self,
        storage: Storage,
        plugins: dict[str, AdapterPlugin],
        bus: EventBus,
        clock: Clock,
        settings: SupervisorSettings | None = None,
        entitlements: Entitlements | None = None,
    ) -> None:
        self._storage = storage
        self._plugins = plugins
        self._bus = bus
        self._clock = clock
        self._settings = settings or SupervisorSettings()
        self._entitlements = entitlements  # ``None``: no limit on the number of TVs
        self._workers: dict[str, TvWorker] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._limited: set[str] = set()
        self._stopping = False

    async def start(self) -> None:
        self._stopping = False
        await self.refresh()

    async def refresh(self, tv_id: str | None = None) -> None:
        """Reconcile with the stored TVs. With ``tv_id`` that TV is restarted from fresh data."""
        records = {record.id: record for record in await self._storage.tvs.list()}
        admitted = self._admit(list(records.values()))
        if tv_id is not None:
            await self._stop_worker(tv_id)
        for stale in set(self._tasks) - admitted:
            await self._stop_worker(stale)
        for record in records.values():
            if record.id in admitted and record.id not in self._tasks:
                self._launch(record)

    def plan_limited(self, tv_id: str) -> bool:
        """Whether the plan keeps this TV from being supervised (it stays configured)."""
        return tv_id in self._limited

    def nudge(self, tv_id: str) -> None:
        """Make the worker of ``tv_id`` re-evaluate now, without reconnecting to the TV."""
        worker = self._workers.get(tv_id)
        if worker is not None:
            worker.nudge()

    async def inventory(self, tv_id: str) -> Inventory | None:
        """The TV's apps, inputs and channels; ``None`` when no worker watches it.

        Raises ``TVError`` while the TV is not connected.
        """
        worker = self._workers.get(tv_id)
        return None if worker is None else await worker.inventory()

    def status(self, tv_id: str) -> TvStatus | None:
        worker = self._workers.get(tv_id)
        return None if worker is None else worker.status

    def statuses(self) -> list[TvStatus]:
        return [worker.status for worker in self._workers.values()]

    async def stop(self) -> None:
        self._stopping = True
        for tv_id in list(self._tasks):
            await self._stop_worker(tv_id)

    def _admit(self, records: list[TvRecord]) -> set[str]:
        """The ids to supervise: the oldest wanted TVs, as many as the plan allows."""
        wanted = sorted((r for r in records if self._wanted(r)), key=lambda r: (r.created_at, r.id))
        limit = self._entitlements.max_tvs() if self._entitlements else None
        admitted = wanted if limit is None else wanted[:limit]
        self._limited = {r.id for r in wanted[len(admitted) :]}
        for record in wanted[len(admitted) :]:
            log.info("TV %s is not supervised: the Free plan covers %s TV(s)", record.id, limit)
        return {r.id for r in admitted}

    def _wanted(self, record: TvRecord) -> bool:
        if not record.enabled:
            return False
        if record.adapter_id not in self._plugins:
            log.warning(
                "TV %s needs adapter %r, which is not installed", record.id, record.adapter_id
            )
            return False
        return True

    def _launch(self, record: TvRecord) -> None:
        worker = TvWorker(
            record,
            self._plugins[record.adapter_id],
            self._storage,
            self._bus,
            self._clock,
            self._settings,
            ProfileService(self._storage, self._clock, self._entitlements),
        )
        task = asyncio.create_task(worker.run(), name=f"tv-{record.id}")
        self._workers[record.id] = worker
        self._tasks[record.id] = task
        task.add_done_callback(lambda done: self._exited(record.id, task, done))

    def _exited(self, tv_id: str, task: asyncio.Task[None], done: asyncio.Task[None]) -> None:
        if done.cancelled() or self._tasks.get(tv_id) is not task:
            return  # stopped on purpose, or already replaced
        log.error("worker of TV %s exited unexpectedly: %r", tv_id, done.exception())
        if self._stopping:
            return
        del self._tasks[tv_id]
        asyncio.get_running_loop().create_task(self._relaunch(tv_id))

    async def _relaunch(self, tv_id: str) -> None:
        if not self._stopping and tv_id not in self._tasks:
            await self.refresh(tv_id)

    async def _stop_worker(self, tv_id: str) -> None:
        task = self._tasks.pop(tv_id, None)
        self._workers.pop(tv_id, None)
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task
