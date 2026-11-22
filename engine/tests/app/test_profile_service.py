from collections.abc import AsyncIterator
from datetime import date, time, timedelta
from pathlib import Path

import pytest
from support import T0, FakeClock

from tvbalance.app.profiles import ProfileService
from tvbalance.config import EngineConfig
from tvbalance.domain.models import Policy
from tvbalance.domain.profiles import DatedEntry, ProfileSource, WeeklyEntry
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import NotFoundError, Storage


class Plan:
    def __init__(self, pro: bool) -> None:
        self.pro = pro

    def is_pro(self) -> bool:
        return self.pro

    def max_tvs(self) -> int | None:
        return None if self.pro else 1


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FakeClock())
    yield store
    await store.close()


async def policy(storage: Storage, name: str = "Holidays") -> int:
    return await storage.policies.create(name, Policy())


async def test_an_activation_applies_to_every_tv_until_it_ends(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    policy_id = await policy(storage)
    await service.activate(policy_id, T0 + timedelta(hours=2))
    found = await service.active_for("any-tv", T0)
    assert found is not None
    assert (found.policy_id, found.until, found.source) == (
        policy_id,
        T0 + timedelta(hours=2),
        ProfileSource.MANUAL,
    )
    assert await service.active_for("any-tv", T0 + timedelta(hours=2)) is None


async def test_excluded_tvs_keep_their_own_rules(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    await service.activate(await policy(storage), T0 + timedelta(hours=1), frozenset({"parents"}))
    assert await service.active_for("parents", T0) is None
    assert await service.active_for("kids", T0) is not None


async def test_stopping_ends_the_profile(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    await service.activate(await policy(storage), T0 + timedelta(hours=1))
    assert await service.stop() == 1
    assert await service.active_for("tv", T0) is None


async def test_an_end_in_the_past_is_refused(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    with pytest.raises(ValueError, match="future"):
        await service.activate(await policy(storage), T0)


async def test_an_unknown_policy_is_not_found(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    with pytest.raises(NotFoundError):
        await service.activate(999, T0 + timedelta(hours=1))


async def test_the_calendar_applies_when_nothing_is_activated(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock(), Plan(pro=True))
    policy_id = await policy(storage)
    await storage.profiles.add_entry(DatedEntry(policy_id, T0.date(), T0.date()))
    found = await service.active_for("tv", T0)
    assert found is not None and found.source is ProfileSource.CALENDAR
    other = await policy(storage, "Weekend")
    await storage.profiles.add_entry(WeeklyEntry(other, frozenset(range(7)), time(0), time(0)))
    await service.activate(other, T0 + timedelta(hours=1))
    found = await service.active_for("tv", T0)
    assert found is not None and found.source is ProfileSource.MANUAL


async def test_without_pro_everything_is_stored_but_ignored(storage: Storage) -> None:
    plan = Plan(pro=False)
    service = ProfileService(storage, FakeClock(), plan)
    policy_id = await policy(storage)
    await service.activate(policy_id, T0 + timedelta(hours=1))
    await storage.profiles.add_entry(DatedEntry(policy_id, date(2026, 1, 1), date(2030, 1, 1)))
    assert not service.effective
    assert await service.active_for("tv", T0) is None
    plan.pro = True  # a license arrives: nothing was lost
    assert await service.active_for("tv", T0) is not None


async def test_without_entitlements_nothing_is_gated(storage: Storage) -> None:
    service = ProfileService(storage, FakeClock())
    assert service.effective
