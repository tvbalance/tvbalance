import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from support import FAST, OPEN, FakeClock, ScriptedTV, eventually, plugin_for, watching

from tvbalance.app.events import EventBus
from tvbalance.app.supervisor import Supervisor
from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FakeClock())
    yield store
    await store.close()


def supervisor(storage: Storage, *tvs: ScriptedTV) -> Supervisor:
    plugins = {f"fake{i}": plugin_for(tv, adapter_id=f"fake{i}") for i, tv in enumerate(tvs)}
    return Supervisor(storage, plugins, EventBus(storage.events), FakeClock(), FAST)


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
