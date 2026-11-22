from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest

from tvbalance.config import EngineConfig
from tvbalance.domain.models import Policy
from tvbalance.domain.profiles import DatedEntry, ProfileActivation, ProfileSource, WeeklyEntry
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import NotFoundError, Storage

T0 = datetime(2026, 11, 16, 20, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return T0


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FixedClock())
    yield store
    await store.close()


async def make_policy(storage: Storage, name: str = "Holidays") -> int:
    return await storage.policies.create(name, Policy())


def activation(
    policy_id: int, start: datetime = T0, hours: int = 2, **extra: object
) -> ProfileActivation:
    return ProfileActivation(policy_id, start, start + timedelta(hours=hours), **extra)  # type: ignore[arg-type]


# --- activations ----------------------------------------------------------------------------


async def test_an_activation_round_trips(storage: Storage) -> None:
    policy_id = await make_policy(storage)
    saved = activation(
        policy_id, excluded_tv_ids=frozenset({"a", "b"}), source=ProfileSource.AUTOMATION
    )
    await storage.profiles.activate(saved, T0)
    assert await storage.profiles.active(T0) == (saved,)


async def test_only_activations_in_force_are_returned(storage: Storage) -> None:
    policy_id = await make_policy(storage)
    await storage.profiles.activate(activation(policy_id, T0 - timedelta(hours=5), 1), T0)
    await storage.profiles.activate(activation(policy_id, T0 + timedelta(hours=1), 1), T0)
    assert await storage.profiles.active(T0) == ()
    assert len(await storage.profiles.active(T0 + timedelta(hours=1))) == 1


async def test_a_new_activation_ends_the_one_in_force(storage: Storage) -> None:
    first, second = await make_policy(storage, "A"), await make_policy(storage, "B")
    await storage.profiles.activate(activation(first, T0 - timedelta(hours=1), 5), T0)
    await storage.profiles.activate(activation(second), T0)
    (live,) = await storage.profiles.active(T0)
    assert live.policy_id == second


async def test_stopping_ends_every_activation_in_force(storage: Storage) -> None:
    policy_id = await make_policy(storage)
    await storage.profiles.activate(activation(policy_id), T0)
    assert await storage.profiles.stop(T0) == 1
    assert await storage.profiles.active(T0) == ()
    assert await storage.profiles.stop(T0) == 0


async def test_activating_an_unknown_policy_is_not_found(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.profiles.activate(activation(999), T0)


# --- calendar -------------------------------------------------------------------------------


async def test_calendar_entries_round_trip_in_creation_order(storage: Storage) -> None:
    policy_id = await make_policy(storage)
    weekly = WeeklyEntry(policy_id, frozenset({4, 5}), time(22, 30), time(6), frozenset({"x"}))
    dated = DatedEntry(policy_id, date(2026, 12, 24), date(2027, 1, 6))
    first = await storage.profiles.add_entry(weekly)
    second = await storage.profiles.add_entry(dated)
    records = await storage.profiles.entries()
    assert [(r.id, r.entry) for r in records] == [(first, weekly), (second, dated)]


async def test_an_entry_can_be_replaced_and_deleted(storage: Storage) -> None:
    policy_id = await make_policy(storage)
    entry_id = await storage.profiles.add_entry(
        DatedEntry(policy_id, date(2026, 12, 24), date(2026, 12, 26))
    )
    changed = WeeklyEntry(policy_id, frozenset({0}), time(8), time(9))
    assert await storage.profiles.update_entry(entry_id, changed) is True
    assert [r.entry for r in await storage.profiles.entries()] == [changed]
    assert await storage.profiles.update_entry(999, changed) is False
    assert await storage.profiles.delete_entry(entry_id) is True
    assert await storage.profiles.delete_entry(entry_id) is False
    assert await storage.profiles.entries() == ()


async def test_an_entry_for_an_unknown_policy_is_not_found(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.profiles.add_entry(DatedEntry(999, date(2026, 12, 24), date(2026, 12, 26)))
    policy_id = await make_policy(storage)
    entry_id = await storage.profiles.add_entry(
        WeeklyEntry(policy_id, frozenset({0}), time(8), time(9))
    )
    with pytest.raises(NotFoundError):
        await storage.profiles.update_entry(
            entry_id, WeeklyEntry(999, frozenset({0}), time(8), time(9))
        )
