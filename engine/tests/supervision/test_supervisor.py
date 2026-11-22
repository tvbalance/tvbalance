import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from support import FAST, OPEN, FakeClock, ScriptedTV, eventually, plugin_for, watching

from tvbalance.app.events import EventBus
from tvbalance.app.supervisor import Supervisor
from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.services import Entitlements
from tvbalance.ports.storage import Storage


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def storage(tmp_path: Path, clock: FakeClock) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), clock)
    yield store
    await store.close()


def supervisor(
    storage: Storage, *tvs: ScriptedTV, entitlements: Entitlements | None = None
) -> Supervisor:
    plugins = {f"fake{i}": plugin_for(tv, adapter_id=f"fake{i}") for i, tv in enumerate(tvs)}
    return Supervisor(storage, plugins, EventBus(storage.events), FakeClock(), FAST, entitlements)


class Plan:
    """An ``Entitlements`` whose limit the test changes."""

    def __init__(self, max_tvs: int | None) -> None:
        self.limit = max_tvs

    def is_pro(self) -> bool:
        return self.limit is None

    def max_tvs(self) -> int | None:
        return self.limit


async def pair(storage: Storage, adapter: str = "fake0", name: str = "TV") -> str:
    return (await storage.tvs.add(adapter, name, "tv.local", {"client_key": "k"})).id


async def test_every_enabled_tv_with_an_adapter_is_supervised(storage: Storage) -> None:
    first, second = ScriptedTV(observation=watching()), ScriptedTV(observation=watching())
    a = await pair(storage, "fake0")
    b = await pair(storage, "fake1")
    sup = supervisor(storage, first, second)
    await sup.start()
    try:
        await eventually(lambda: first.observe_calls > 0 and second.observe_calls > 0)
        assert {s.tv_id for s in sup.statuses()} == {a, b}
        assert sup.status(a) is not None
        assert sup.status("nope") is None
    finally:
        await sup.stop()
    assert not first.connected and not second.connected


async def test_a_tv_with_a_missing_adapter_is_skipped(
    storage: Storage, caplog: pytest.LogCaptureFixture
) -> None:
    tv = ScriptedTV(observation=watching())
    missing = await pair(storage, "gone")
    good = await pair(storage, "fake0")
    sup = supervisor(storage, tv)
    await sup.start()
    try:
        await eventually(lambda: tv.observe_calls > 0)
        assert sup.status(missing) is None
        assert sup.status(good) is not None
    finally:
        await sup.stop()
    assert "gone" in caplog.text


async def test_a_disabled_tv_is_not_supervised(storage: Storage) -> None:
    tv = ScriptedTV(observation=watching())
    tv_id = await pair(storage)
    await storage.tvs.set_enabled(tv_id, False)
    sup = supervisor(storage, tv)
    await sup.start()
    await asyncio.sleep(0.1)
    await sup.stop()
    assert tv.connect_calls == 0


async def test_refresh_restarts_one_tv_with_fresh_data(storage: Storage) -> None:
    tv = ScriptedTV(observation=watching())
    tv_id = await pair(storage)
    sup = supervisor(storage, tv)
    await sup.start()
    try:
        await eventually(lambda: tv.connect_calls == 1)
        await sup.refresh(tv_id)
        await eventually(lambda: tv.connect_calls == 2)
    finally:
        await sup.stop()


async def test_refresh_all_picks_up_new_tvs_and_drops_removed_ones(storage: Storage) -> None:
    tv = ScriptedTV(observation=watching())
    first = await pair(storage, name="one")
    sup = supervisor(storage, tv)
    await sup.start()
    try:
        second = await pair(storage, name="two")
        await sup.refresh()
        await eventually(lambda: sup.status(second) is not None)
        await storage.tvs.remove(first)
        await sup.refresh()
        assert sup.status(first) is None
        assert tv.connect_calls >= 2
    finally:
        await sup.stop()


async def test_a_worker_that_exits_unexpectedly_is_restarted(
    storage: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tvbalance.app import supervisor as module

    tv = ScriptedTV(observation=watching())
    await pair(storage)
    real = module.TvWorker.run
    runs = 0

    async def crashing(self: module.TvWorker) -> None:
        nonlocal runs
        runs += 1
        if runs == 1:
            raise RuntimeError("boom")
        await real(self)

    monkeypatch.setattr(module.TvWorker, "run", crashing)
    sup = supervisor(storage, tv)
    await sup.start()
    try:
        await eventually(lambda: runs >= 2 and tv.observe_calls > 0)
    finally:
        await sup.stop()


async def test_stop_is_idempotent_and_leaves_nothing_running(storage: Storage) -> None:
    tv = ScriptedTV(observation=watching())
    await pair(storage)
    policy_id = await storage.policies.create("p", OPEN)
    sup = supervisor(storage, tv)
    await sup.start()
    await eventually(lambda: tv.connect_calls > 0)
    await sup.stop()
    await sup.stop()
    assert sup.statuses() == []
    assert policy_id


async def _two_tvs(storage: Storage, clock: FakeClock) -> tuple[str, str]:
    older = await pair(storage, "fake0", "Older")
    clock.advance(minutes=1)
    newer = await pair(storage, "fake1", "Newer")
    return older, newer


async def test_free_plan_supervises_only_the_oldest_enabled_tv(
    storage: Storage, clock: FakeClock
) -> None:
    first, second = ScriptedTV(observation=watching()), ScriptedTV(observation=watching())
    older, newer = await _two_tvs(storage, clock)
    sup = supervisor(storage, first, second, entitlements=Plan(1))
    await sup.start()
    try:
        await eventually(lambda: first.observe_calls > 0)
        assert sup.status(older) is not None and sup.status(newer) is None
        assert not sup.plan_limited(older) and sup.plan_limited(newer)
        assert second.connect_calls == 0
    finally:
        await sup.stop()


async def test_a_license_starts_the_limited_tv_and_its_end_stops_it(
    storage: Storage, clock: FakeClock
) -> None:
    first, second = ScriptedTV(observation=watching()), ScriptedTV(observation=watching())
    older, newer = await _two_tvs(storage, clock)
    plan = Plan(1)
    sup = supervisor(storage, first, second, entitlements=plan)
    await sup.start()
    try:
        plan.limit = None
        await sup.refresh()
        await eventually(lambda: second.observe_calls > 0)
        assert sup.status(newer) is not None and not sup.plan_limited(newer)
        plan.limit = 1
        await sup.refresh()
        assert sup.status(newer) is None and sup.plan_limited(newer)
        assert sup.status(older) is not None
    finally:
        await sup.stop()


async def test_disabling_the_oldest_tv_lets_the_next_one_in(
    storage: Storage, clock: FakeClock
) -> None:
    first, second = ScriptedTV(observation=watching()), ScriptedTV(observation=watching())
    older, newer = await _two_tvs(storage, clock)
    sup = supervisor(storage, first, second, entitlements=Plan(1))
    await sup.start()
    try:
        await storage.tvs.set_enabled(older, False)
        await sup.refresh(older)
        await eventually(lambda: second.observe_calls > 0)
        assert sup.status(older) is None and sup.status(newer) is not None
        assert not sup.plan_limited(newer) and not sup.plan_limited(older)
    finally:
        await sup.stop()


async def test_a_tv_without_an_adapter_does_not_use_up_the_free_slot(
    storage: Storage, clock: FakeClock
) -> None:
    tv = ScriptedTV(observation=watching())
    await pair(storage, "gone", "Orphan")
    clock.advance(minutes=1)
    good = await pair(storage, "fake0", "Good")
    sup = supervisor(storage, tv, entitlements=Plan(1))
    await sup.start()
    try:
        await eventually(lambda: tv.observe_calls > 0)
        assert sup.status(good) is not None
    finally:
        await sup.stop()
