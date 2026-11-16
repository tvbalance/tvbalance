import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytest
from support import (
    CLOSED,
    FAST,
    OPEN,
    T0,
    FakeClock,
    ScriptedTV,
    eventually,
    kinds,
    pairing_rejected,
    plugin_for,
    watching,
)

from tvbalance.app.events import BusEvent, EventBus
from tvbalance.app.worker import TvWorker
from tvbalance.config import EngineConfig
from tvbalance.domain.models import (
    GoHome,
    MessageKind,
    Observation,
    Override,
    Policy,
    Power,
    PowerOff,
    ShowMessage,
)
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage, TvRecord
from tvbalance.sdk.errors import TVError, TVTimeoutError
from tvbalance.sdk.types import Capability


@dataclass
class World:
    storage: Storage
    clock: FakeClock
    bus: EventBus
    tv: ScriptedTV
    queue: asyncio.Queue[BusEvent]
    record: TvRecord

    def worker(self, capabilities: frozenset[Capability] | None = None) -> TvWorker:
        return TvWorker(
            self.record, plugin_for(self.tv, capabilities), self.storage, self.bus, self.clock, FAST
        )

    async def assign(self, policy: Policy) -> None:
        policy_id = await self.storage.policies.create("test", policy)
        await self.storage.tvs.assign_policy(self.record.id, policy_id)

    async def usage(self) -> int:
        return (await self.storage.usage.get(self.record.id, T0.date())).watched_seconds


@pytest.fixture
async def world(tmp_path: Path) -> AsyncIterator[World]:
    clock = FakeClock()
    storage = await open_storage(EngineConfig(data_dir=tmp_path / "data"), clock)
    await storage.settings.set("timezone", "Europe/Rome")
    record = await storage.tvs.add("fake", "Living room", "tv.local", {"client_key": "k"})
    bus = EventBus(storage.events)
    tv = ScriptedTV(observation=watching("video"))
    async with bus.subscribe() as queue:
        yield World(storage, clock, bus, tv, queue, record)
    await storage.close()


async def live(world: World, policy: Policy | None = OPEN) -> TvWorker:
    if policy is not None:
        await world.assign(policy)
    worker = world.worker()
    assert await worker.connect()
    return worker


def messages(tv: ScriptedTV) -> list[ShowMessage]:
    return [a for a in tv.executed if isinstance(a, ShowMessage)]


# --- usage and enforcement ------------------------------------------------------------------


async def test_allowed_viewing_is_counted_and_left_alone(world: World) -> None:
    worker = await live(world)
    await worker.tick()
    world.clock.advance(seconds=30)
    await worker.tick()
    assert await world.usage() == 30
    assert world.tv.executed == []
    assert worker.status.connected
    assert worker.status.watched_seconds == 30


async def test_blocked_app_gets_a_message_then_goes_home(world: World) -> None:
    world.tv.observation = watching("tiktok")
    worker = await live(world)
    await worker.tick()
    assert world.tv.executed == []  # debounce: nothing yet
    world.clock.advance(seconds=3)
    await worker.tick()
    assert [type(a) for a in world.tv.executed] == [ShowMessage, GoHome]
    assert messages(world.tv)[0].text  # localized before reaching the TV
    assert "blocked" in kinds(world.queue)


async def test_time_up_shows_the_message_then_powers_off(world: World) -> None:
    worker = await live(world, CLOSED)
    await worker.tick()
    world.clock.advance(seconds=3)
    await worker.tick()
    assert messages(world.tv)[0].kind is MessageKind.TIME_UP
    world.clock.advance(seconds=18)
    await worker.tick()
    assert any(isinstance(a, PowerOff) for a in world.tv.executed)
    assert "powered_off" in kinds(world.queue)


async def test_a_block_override_stops_viewing(world: World) -> None:
    worker = await live(world)
    until = T0 + timedelta(hours=1)
    await world.storage.overrides.add(world.record.id, Override(False, until, T0))
    await worker.tick()
    world.clock.advance(seconds=3)
    await worker.tick()
    assert messages(world.tv)


async def test_messages_follow_the_language_setting(world: World) -> None:
    await world.storage.settings.set("language", "it")
    worker = await live(world, CLOSED)
    await worker.tick()
    world.clock.advance(seconds=3)
    await worker.tick()
    text = messages(world.tv)[0].text or ""
    assert "tempo" in text.lower()


async def test_warning_five_minutes_before_the_window_ends(world: World) -> None:
    from datetime import time

    from tvbalance.domain.models import Schedule, TimeWindow

    until_1805 = Schedule(windows={1: (TimeWindow(time(0), time(18, 5)),)})  # Tuesday
    worker = await live(world, Policy(schedule=until_1805))
    await worker.tick()
    assert "time_warning" in kinds(world.queue)
    assert messages(world.tv)[0].kind is MessageKind.TIME_WARNING


async def test_without_a_policy_the_tv_is_only_watched(world: World) -> None:
    worker = await live(world, None)
    await worker.tick()
    world.clock.advance(seconds=30)
    await worker.tick()
    assert world.tv.executed == []
    assert await world.usage() == 30


async def test_an_invalid_timezone_falls_back_to_the_system_zone(world: World) -> None:
    await world.storage.settings.set("timezone", "Mars/Olympus")
    worker = await live(world)
    await worker.tick()
    assert worker.status.observation is not None


# --- persistence ----------------------------------------------------------------------------


async def test_enforcement_state_survives_a_restart(world: World) -> None:
    world.tv.observation = watching("tiktok")
    worker = await live(world)
    await worker.tick()
    world.clock.advance(seconds=3)
    await worker.tick()
    world.tv.executed.clear()

    restarted = world.worker()
    assert await restarted.connect()
    world.clock.advance(seconds=1)
    await restarted.tick()  # same episode: the message is not repeated at once
    assert messages(world.tv) == []


# --- connection trouble ---------------------------------------------------------------------


async def test_unreachable_and_reachable_are_reported_once_each(world: World) -> None:
    worker = await live(world)
    await worker.tick()
    world.tv.observe_error = TVError("gone")
    await worker.tick()
    await worker.tick()  # already dropped: nothing more to say
    assert not worker.status.connected
    world.tv.observe_error = None
    assert await worker.connect()
    assert kinds(world.queue) == ["tv_unreachable", "tv_reachable"]


async def test_standby_is_not_an_outage(world: World) -> None:
    world.tv.observation = Observation(observed_at=T0, power=Power.STANDBY)
    worker = await live(world)
    await worker.tick()
    world.tv.observe_error = TVError("gone")
    await worker.tick()
    assert kinds(world.queue) == []


async def test_time_offline_is_not_billed(world: World) -> None:
    worker = await live(world)
    await worker.tick()
    world.tv.observe_error = TVError("gone")
    await worker.tick()
    world.clock.advance(seconds=60)
    world.tv.observe_error = None
    assert await worker.connect()
    await worker.tick()
    assert await world.usage() == 0


async def test_a_hung_observe_does_not_block(world: World) -> None:
    worker = await live(world)
    world.tv.hang_observe = True
    async with asyncio.timeout(2):
        await worker.tick()
    assert not worker.status.connected


async def test_a_refused_key_reports_pairing_lost_and_parks(world: World) -> None:
    world.tv.connect_error = pairing_rejected()
    worker = world.worker()
    assert not await worker.connect()
    assert worker.status.pairing_required
    assert kinds(world.queue) == ["pairing_lost"]


async def test_unreadable_credentials_mean_pairing_without_connecting(world: World) -> None:
    from dataclasses import replace

    world.record = replace(world.record, needs_pairing=True)
    worker = world.worker()
    assert not await worker.connect()
    assert world.tv.connect_calls == 0
    assert kinds(world.queue) == ["pairing_lost"]


async def test_run_reconnects_with_backoff(world: World) -> None:
    world.tv.connect_error = TVError("down")
    task = asyncio.create_task(world.worker().run())
    try:
        await eventually(lambda: world.tv.connect_calls >= 3)
        world.tv.connect_error = None
        await eventually(lambda: world.tv.observe_calls >= 1)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_a_pairing_failure_is_not_retried(world: World) -> None:
    world.tv.connect_error = pairing_rejected()
    task = asyncio.create_task(world.worker().run())
    try:
        await eventually(lambda: world.tv.connect_calls >= 1)
        await asyncio.sleep(0.15)
        assert world.tv.connect_calls == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


# --- actions that go wrong ------------------------------------------------------------------


async def test_a_failed_action_does_not_stop_the_others(world: World) -> None:
    world.tv.observation = watching("tiktok")
    worker = await live(world)
    await worker.tick()
    world.clock.advance(seconds=3)
    world.tv.fail_execute = True
    await worker.tick()
    assert worker.status.connected  # the TV answered; only the commands failed


async def test_an_execute_timeout_drops_the_session(world: World) -> None:
    world.tv.observation = watching("tiktok")
    worker = await live(world)
    await worker.tick()
    world.clock.advance(seconds=3)
    world.tv.hang_execute = True
    await worker.tick()
    assert not worker.status.connected


async def test_a_tick_failure_does_not_kill_run(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    real = world.storage.usage.get

    async def flaky(tv_id: str, day: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database is locked")
        return await real(tv_id, day)  # type: ignore[arg-type]

    monkeypatch.setattr(world.storage.usage, "get", flaky)
    task = asyncio.create_task(world.worker().run())
    try:
        await eventually(lambda: calls >= 3)
        assert not task.done()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_cancelling_run_closes_the_session(world: World) -> None:
    task = asyncio.create_task(world.worker().run())
    await eventually(lambda: world.tv.connected)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert not world.tv.connected


# --- push -----------------------------------------------------------------------------------


async def test_a_push_wakes_the_loop_before_the_next_poll(world: World) -> None:
    slow = FAST.__class__(
        tick_interval=30.0, backoff_min=0.01, backoff_max=0.04, timeouts=FAST.timeouts
    )
    worker = TvWorker(
        world.record, plugin_for(world.tv), world.storage, world.bus, world.clock, slow
    )
    task = asyncio.create_task(worker.run())
    try:
        await eventually(lambda: world.tv.observe_calls >= 1 and bool(world.tv.listeners))
        before = world.tv.observe_calls
        world.tv.changed()
        await eventually(lambda: world.tv.observe_calls > before)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_without_the_push_capability_nothing_is_subscribed(world: World) -> None:
    worker = world.worker(frozenset({Capability.POWER_OFF}))
    assert await worker.connect()
    assert world.tv.listeners == []


def test_timeout_errors_are_tv_errors() -> None:
    assert issubclass(TVTimeoutError, TVError)
