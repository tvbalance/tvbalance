from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from support import FakeClock

from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage

ENDPOINT = "https://push.example.net/send/abc"
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
KEY = "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
EVENTS = frozenset({"blocked", "pairing_lost"})


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def storage(tmp_path: Path, clock: FakeClock) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), clock)
    yield store
    await store.close()


async def add(storage: Storage, endpoint: str = ENDPOINT, events: frozenset[str] = EVENTS):
    return await storage.push.upsert(
        endpoint, KEY, AUTH, events, "it", "https://ha.local/app", "Firefox"
    )


async def test_a_subscription_round_trips(storage: Storage, clock: FakeClock) -> None:
    record, created = await add(storage)
    assert created
    assert record.endpoint == ENDPOINT and record.p256dh == KEY and record.auth == AUTH
    assert record.events == EVENTS and record.language == "it"
    assert record.app_url == "https://ha.local/app" and record.user_agent == "Firefox"
    assert record.created_at == clock.now() and record.last_sent_at is None and record.failures == 0
    assert await storage.push.get(record.id) == record
    assert await storage.push.list() == [record]


async def test_subscribing_again_updates_the_same_row(storage: Storage) -> None:
    first, _ = await add(storage)
    second, created = await storage.push.upsert(
        ENDPOINT, KEY, AUTH, frozenset({"blocked"}), "de", "https://other/", "Chrome"
    )
    assert not created and second.id == first.id
    assert second.events == frozenset({"blocked"}) and second.language == "de"
    assert len(await storage.push.list()) == 1


async def test_the_auth_secret_is_sealed_on_disk(tmp_path: Path, clock: FakeClock) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    store = await open_storage(config, clock)
    await add(store)
    await store.close()
    raw = (config.data_dir / "tvbalance.db").read_bytes()
    assert AUTH.encode() not in raw
    again = await open_storage(config, clock)
    try:
        assert (await again.push.list())[0].auth == AUTH
    finally:
        await again.close()


async def test_events_can_be_changed_and_a_missing_id_is_reported(storage: Storage) -> None:
    record, _ = await add(storage)
    assert await storage.push.update_events(record.id, frozenset()) is True
    assert (await storage.push.get(record.id)).events == frozenset()  # type: ignore[union-attr]
    assert await storage.push.update_events("nope", EVENTS) is False


async def test_delete_removes_only_that_subscription(storage: Storage) -> None:
    first, _ = await add(storage)
    second, _ = await add(storage, "https://push.example.net/send/other")
    assert await storage.push.delete(first.id) is True
    assert await storage.push.delete(first.id) is False
    assert [r.id for r in await storage.push.list()] == [second.id]


async def test_failures_count_up_and_a_delivery_resets_them(
    storage: Storage, clock: FakeClock
) -> None:
    record, _ = await add(storage)
    assert await storage.push.record_failure(record.id) == 1
    assert await storage.push.record_failure(record.id) == 2
    await storage.push.record_delivery(record.id)
    after = await storage.push.get(record.id)
    assert after is not None and after.failures == 0 and after.last_sent_at == clock.now()
    assert await storage.push.record_failure("nope") == 0
