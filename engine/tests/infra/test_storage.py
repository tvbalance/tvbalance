import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tvbalance.config import EngineConfig
from tvbalance.domain.models import AppTarget, Override, Policy, Usage
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import NotFoundError, Storage

T0 = datetime(2026, 11, 16, 20, 0, tzinfo=UTC)
DAY = date(2026, 11, 16)
SECRET = "SUPER-SECRET-CLIENT-KEY"


class FixedClock:
    def __init__(self) -> None:
        self.current = T0

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def config(tmp_path: Path) -> EngineConfig:
    return EngineConfig(data_dir=tmp_path / "data")


@pytest.fixture
async def storage(config: EngineConfig, clock: FixedClock) -> AsyncIterator[Storage]:
    store = await open_storage(config, clock)
    yield store
    await store.close()


async def add_tv(storage: Storage, name: str = "Living room") -> str:
    tv = await storage.tvs.add("webos", name, "tv.local", {"client_key": SECRET})
    return tv.id


# --- open_storage ---------------------------------------------------------------------------


async def test_open_storage_creates_the_data_directory_and_files(config: EngineConfig) -> None:
    store = await open_storage(config)
    await store.close()
    assert (config.data_dir / "tvbalance.db").is_file()
    assert (config.data_dir / "secret.key").is_file()


async def test_data_survives_closing_and_reopening(config: EngineConfig, clock: FixedClock) -> None:
    first = await open_storage(config, clock)
    tv_id = await add_tv(first)
    await first.settings.set("language", "it")
    await first.close()

    second = await open_storage(config, clock)
    try:
        tv = await second.tvs.get(tv_id)
        assert tv is not None and tv.credentials == {"client_key": SECRET}
        assert await second.settings.get("language") == "it"
    finally:
        await second.close()


# --- TVs ------------------------------------------------------------------------------------


async def test_a_tv_round_trips(storage: Storage) -> None:
    tv = await storage.tvs.add("webos", "Living room", "tv.local", {"client_key": "k"})
    assert (tv.adapter_id, tv.name, tv.host) == ("webos", "Living room", "tv.local")
    assert tv.credentials == {"client_key": "k"}
    assert (tv.policy_id, tv.enabled, tv.created_at, tv.needs_pairing) == (None, True, T0, False)
    assert await storage.tvs.get(tv.id) == tv
    assert await storage.tvs.get("missing") is None


async def test_tvs_are_listed_in_creation_order(storage: Storage, clock: FixedClock) -> None:
    first = await add_tv(storage, "First")
    clock.current += timedelta(minutes=1)
    second = await add_tv(storage, "Second")
    assert [tv.id for tv in await storage.tvs.list()] == [first, second]


async def test_credentials_are_not_readable_in_the_database_files(
    storage: Storage, config: EngineConfig
) -> None:
    await add_tv(storage)
    stored = b"".join(p.read_bytes() for p in config.data_dir.glob("tvbalance.db*"))
    assert stored and SECRET.encode() not in stored


async def test_credentials_stay_out_of_the_repr(storage: Storage) -> None:
    tv = await storage.tvs.add("webos", "TV", "tv.local", {"client_key": SECRET})
    assert SECRET not in repr(tv)


async def test_credentials_can_be_replaced(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await storage.tvs.update_credentials(tv_id, {"client_key": "new"})
    tv = await storage.tvs.get(tv_id)
    assert tv is not None and tv.credentials == {"client_key": "new"} and not tv.needs_pairing


async def test_a_lost_secret_key_asks_for_pairing_instead_of_breaking(
    config: EngineConfig, clock: FixedClock
) -> None:
    first = await open_storage(config, clock)
    tv_id = await add_tv(first)
    await first.close()
    (config.data_dir / "secret.key").unlink()

    second = await open_storage(config, clock)
    try:
        (tv,) = await second.tvs.list()
        assert tv.id == tv_id and tv.needs_pairing and tv.credentials == {}
        await second.tvs.update_credentials(tv_id, {"client_key": "fresh"})
        again = await second.tvs.get(tv_id)
        assert again is not None and not again.needs_pairing
    finally:
        await second.close()


async def test_a_policy_can_be_assigned_and_cleared(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    policy_id = await storage.policies.create("School", Policy())
    await storage.tvs.assign_policy(tv_id, policy_id)
    assert (await storage.tvs.get(tv_id)).policy_id == policy_id  # type: ignore[union-attr]
    await storage.tvs.assign_policy(tv_id, None)
    assert (await storage.tvs.get(tv_id)).policy_id is None  # type: ignore[union-attr]


async def test_unknown_tv_or_policy_is_not_found(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    with pytest.raises(NotFoundError):
        await storage.tvs.assign_policy(tv_id, 999)
    with pytest.raises(NotFoundError):
        await storage.tvs.assign_policy("missing", None)
    with pytest.raises(NotFoundError):
        await storage.tvs.update_credentials("missing", {})
    with pytest.raises(NotFoundError):
        await storage.tvs.add("webos", "TV", "h", {}, policy_id=999)


async def test_removing_a_tv_removes_its_usage_and_overrides_but_keeps_events(
    storage: Storage,
) -> None:
    tv_id = await add_tv(storage)
    other = await add_tv(storage, "Bedroom")
    for tv in (tv_id, other):
        await storage.usage.add_watched(tv, DAY, 60)
        await storage.overrides.add(tv, Override(True, T0 + timedelta(hours=1), T0))
        await storage.events.append(tv, "blocked", {"why": "window"}, T0)

    assert await storage.tvs.remove(tv_id) is True
    assert await storage.tvs.remove(tv_id) is False

    assert await storage.tvs.get(tv_id) is None
    assert await storage.usage.get(tv_id, DAY) == Usage(DAY)
    assert await storage.overrides.active(tv_id, T0) == ()
    assert (await storage.usage.get(other, DAY)).watched_seconds == 60
    assert len(await storage.overrides.active(other, T0)) == 1
    events = await storage.events.recent(None, T0 - timedelta(days=1))
    assert sorted(e.tv_id or "-" for e in events) == sorted(["-", other])


# --- policies -------------------------------------------------------------------------------


async def test_a_policy_round_trips(storage: Storage) -> None:
    policy = Policy(daily_budget_minutes=90, fallback=AppTarget("news"))
    policy_id = await storage.policies.create("School", policy)
    record = await storage.policies.get(policy_id)
    assert record is not None
    assert (record.id, record.name, record.policy, record.updated_at) == (
        policy_id,
        "School",
        policy,
        T0,
    )
    assert await storage.policies.get(999) is None


async def test_saving_a_policy_replaces_it(storage: Storage, clock: FixedClock) -> None:
    policy_id = await storage.policies.create("School", Policy())
    clock.current += timedelta(hours=1)
    await storage.policies.save(policy_id, Policy(daily_budget_minutes=30))
    record = await storage.policies.get(policy_id)
    assert record is not None
    assert (record.name, record.policy.daily_budget_minutes, record.updated_at) == (
        "School",
        30,
        clock.current,
    )
    await storage.policies.save(policy_id, Policy(), name="Weekend")
    renamed = await storage.policies.get(policy_id)
    assert renamed is not None and renamed.name == "Weekend"


async def test_saving_an_unknown_policy_is_not_found(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.policies.save(999, Policy())


async def test_policies_are_listed_in_creation_order(storage: Storage) -> None:
    a = await storage.policies.create("A", Policy())
    b = await storage.policies.create("B", Policy())
    assert [r.id for r in await storage.policies.list()] == [a, b]


# --- usage ----------------------------------------------------------------------------------


async def test_a_day_without_viewing_has_zero_usage(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    assert await storage.usage.get(tv_id, DAY) == Usage(DAY, 0, 0)


async def test_usage_accumulates_per_day(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await storage.usage.add_watched(tv_id, DAY, 30)
    await storage.usage.add_watched(tv_id, DAY, 45)
    await storage.usage.add_bonus(tv_id, DAY, 10)
    await storage.usage.add_watched(tv_id, DAY + timedelta(days=1), 5)
    assert await storage.usage.get(tv_id, DAY) == Usage(DAY, 75, 10)
    assert (await storage.usage.get(tv_id, DAY + timedelta(days=1))).watched_seconds == 5


async def test_concurrent_increments_are_never_lost(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await asyncio.gather(
        *(storage.usage.add_watched(tv_id, DAY, 1) for _ in range(40)),
        *(storage.usage.add_bonus(tv_id, DAY, 2) for _ in range(20)),
    )
    assert await storage.usage.get(tv_id, DAY) == Usage(DAY, 40, 40)


async def test_usage_for_an_unknown_tv_is_not_found(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.usage.add_watched("missing", DAY, 5)
    with pytest.raises(NotFoundError):
        await storage.usage.add_bonus("missing", DAY, 5)


# --- overrides ------------------------------------------------------------------------------


async def test_only_unexpired_overrides_are_active_oldest_first(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    newer = Override(False, T0 + timedelta(hours=2), T0 + timedelta(minutes=5))
    older = Override(True, T0 + timedelta(hours=1), T0)
    expired = Override(True, T0, T0 - timedelta(hours=1))
    for override in (newer, expired, older):
        await storage.overrides.add(tv_id, override)
    assert await storage.overrides.active(tv_id, T0) == (older, newer)
    assert await storage.overrides.active(tv_id, T0 + timedelta(hours=1)) == (newer,)


async def test_clearing_overrides_only_touches_that_tv(storage: Storage) -> None:
    tv_id, other = await add_tv(storage), await add_tv(storage, "Bedroom")
    for tv in (tv_id, other):
        await storage.overrides.add(tv, Override(True, T0 + timedelta(hours=1), T0))
    assert await storage.overrides.clear(tv_id) == 1
    assert await storage.overrides.clear(tv_id) == 0
    assert await storage.overrides.active(tv_id, T0) == ()
    assert len(await storage.overrides.active(other, T0)) == 1


async def test_an_override_for_an_unknown_tv_is_not_found(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.overrides.add("missing", Override(True, T0, T0))


# --- events ---------------------------------------------------------------------------------


async def test_events_come_back_newest_first_with_their_payload(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await storage.events.append(tv_id, "time_warning", {"minutes_left": 10}, T0)
    await storage.events.append(
        tv_id, "blocked", {"reason": "outside_window"}, T0 + timedelta(minutes=1)
    )
    events = await storage.events.recent(tv_id, T0 - timedelta(minutes=1))
    assert [e.type for e in events] == ["blocked", "time_warning"]
    assert events[1].payload == {"minutes_left": 10}
    assert events[1].occurred_at == T0 and events[1].tv_id == tv_id


async def test_events_can_be_filtered_by_tv_time_and_limit(storage: Storage) -> None:
    tv_id, other = await add_tv(storage), await add_tv(storage, "Bedroom")
    await storage.events.append(tv_id, "a", {}, T0)
    await storage.events.append(other, "b", {}, T0 + timedelta(minutes=1))
    await storage.events.append(None, "system", {}, T0 + timedelta(minutes=2))
    since = T0 - timedelta(minutes=1)
    assert [e.type for e in await storage.events.recent(tv_id, since)] == ["a"]
    assert [e.type for e in await storage.events.recent(None, since)] == ["system", "b", "a"]
    assert [e.type for e in await storage.events.recent(None, since, limit=2)] == ["system", "b"]
    assert [e.type for e in await storage.events.recent(None, T0 + timedelta(minutes=1))] == [
        "system",
        "b",
    ]


# --- settings -------------------------------------------------------------------------------


async def test_settings_default_overwrite_and_json_values(storage: Storage) -> None:
    assert await storage.settings.get("language") is None
    assert await storage.settings.get("language", "en") == "en"
    await storage.settings.set("language", "it")
    await storage.settings.set("language", "de")
    await storage.settings.set("region", {"country": "IT", "tz": "Europe/Rome"})
    assert await storage.settings.get("language") == "de"
    assert await storage.settings.get("region") == {"country": "IT", "tz": "Europe/Rome"}
