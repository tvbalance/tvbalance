import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from support import FakeClock

from tvbalance.app.events import EventBus
from tvbalance.app.notifications import MAX_FAILURES, PushNotifier, load_vapid_keys
from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import SqliteStorage, open_storage
from tvbalance.infra.webpush import PushTarget, SendResult
from tvbalance.ports.storage import PushSubscriptionRecord

KEY = "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
ALL = frozenset({"pairing_lost", "tv_unreachable", "blocked", "time_warning"})
Sent = tuple[PushTarget, dict[str, str], int, str]


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[Sent] = []
        self.result = SendResult.DELIVERED

    async def send(
        self, target: PushTarget, payload: bytes, *, ttl: int = 3600, urgency: str = "normal"
    ) -> SendResult:
        self.sent.append((target, json.loads(payload), ttl, urgency))
        return self.result


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def storage(tmp_path: Path, clock: FakeClock) -> AsyncIterator[SqliteStorage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), clock)
    yield store
    await store.close()


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()


@pytest.fixture
def notifier(storage: SqliteStorage, sender: FakeSender, clock: FakeClock) -> PushNotifier:
    return PushNotifier(storage, EventBus(storage.events), sender, clock)


async def tv(storage: SqliteStorage) -> str:
    return (await storage.tvs.add("fake", "Living room", "tv.local", {})).id


async def subscribe(
    storage: SqliteStorage,
    events: frozenset[str] = ALL,
    language: str = "en",
    endpoint: str = "https://push.example.net/a",
) -> PushSubscriptionRecord:
    record, _ = await storage.push.upsert(
        endpoint, KEY, AUTH, events, language, "https://ha.local/app/", "UA"
    )
    return record


async def test_pairing_lost_links_to_the_pairing_page_with_high_urgency(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender, clock: FakeClock
) -> None:
    tv_id = await tv(storage)
    sub = await subscribe(storage)
    await notifier.handle(tv_id, "pairing_lost", {"reason": "x"})
    assert len(sender.sent) == 1
    target, payload, ttl, urgency = sender.sent[0]
    assert target == PushTarget(sub.endpoint, KEY, AUTH)
    assert payload["title"] == "Living room"
    assert "pair the TV again" in payload["body"]
    assert payload["url"] == f"https://ha.local/app/#/tvs/{tv_id}/pair"
    assert payload["tag"] == f"pairing_lost:{tv_id}"
    assert (ttl, urgency) == (12 * 3600, "high")
    stored = await storage.push.get(sub.id)
    assert stored is not None and stored.last_sent_at == clock.now()


async def test_blocked_uses_the_reason_and_the_language_of_the_subscription(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage, language="it-IT")
    await notifier.handle(tv_id, "blocked", {"reason": "budget_exhausted"})
    _, payload, _, urgency = sender.sent[0]
    assert payload["body"] == "Il tempo di TV di oggi è esaurito."
    assert payload["url"].endswith(f"#/tvs/{tv_id}") and urgency == "high"


async def test_time_warning_is_short_lived_and_normal_urgency(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage)
    await notifier.handle(tv_id, "time_warning", {"minutes_left": 5, "limit": "daily"})
    await notifier.handle("gone-tv", "time_warning", {"minutes_left": 1, "limit": "daily"})
    (_, first, ttl, urgency), (_, second, _, _) = sender.sent
    assert first["body"] == "5 minutes of TV time left." and (ttl, urgency) == (300, "normal")
    assert first["title"] == "Living room" and second["title"] == "TVBalance"
    assert second["body"] == "1 minute of TV time left."


async def test_only_subscriptions_that_want_the_event_receive_it(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage, frozenset({"blocked"}), endpoint="https://push.example.net/a")
    await subscribe(storage, frozenset({"tv_unreachable"}), endpoint="https://push.example.net/b")
    await notifier.handle(tv_id, "tv_unreachable", {"reason": "x"})
    assert [sent[0].endpoint for sent in sender.sent] == ["https://push.example.net/b"]


@pytest.mark.parametrize("event_type", ["redirected", "powered_off", "tv_reachable", "unknown"])
async def test_other_events_are_ignored(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender, event_type: str
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage)
    await notifier.handle(tv_id, event_type, {})
    await notifier.handle(None, "blocked", {"reason": "override"})
    assert sender.sent == []


async def test_the_same_event_is_not_repeated_within_ten_minutes(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender, clock: FakeClock
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage)
    payload = {"reason": "budget_exhausted"}
    await notifier.handle(tv_id, "blocked", payload)
    clock.advance(minutes=9)
    await notifier.handle(tv_id, "blocked", payload)
    await notifier.handle(tv_id, "blocked", {"reason": "outside_window"})
    assert len(sender.sent) == 2
    clock.advance(minutes=2)
    await notifier.handle(tv_id, "blocked", payload)
    assert len(sender.sent) == 3


async def test_a_gone_subscription_is_removed(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    tv_id = await tv(storage)
    await subscribe(storage)
    sender.result = SendResult.GONE
    await notifier.handle(tv_id, "pairing_lost", {})
    assert await storage.push.list() == []


async def test_repeated_failures_remove_the_subscription(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender, clock: FakeClock
) -> None:
    tv_id = await tv(storage)
    sub = await subscribe(storage)
    sender.result = SendResult.FAILED
    for attempt in range(1, MAX_FAILURES):
        await notifier.handle(tv_id, "pairing_lost", {})
        clock.advance(minutes=11)
        stored = await storage.push.get(sub.id)
        assert stored is not None and stored.failures == attempt
    await notifier.handle(tv_id, "pairing_lost", {})
    assert await storage.push.list() == []


async def test_a_test_notification_goes_to_one_subscription(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    sub = await subscribe(storage, language="de")
    await subscribe(storage, endpoint="https://push.example.net/b")
    assert await notifier.send_test(sub) is SendResult.DELIVERED
    assert len(sender.sent) == 1
    target, payload, _, _ = sender.sent[0]
    assert target.endpoint == sub.endpoint
    assert payload["body"] == "Benachrichtigungen funktionieren."
    assert payload["url"] == "https://ha.local/app/#/settings"


async def test_a_gone_test_target_is_removed(
    storage: SqliteStorage, notifier: PushNotifier, sender: FakeSender
) -> None:
    sub = await subscribe(storage)
    sender.result = SendResult.GONE
    assert await notifier.send_test(sub) is SendResult.GONE
    assert await storage.push.list() == []


async def test_the_notifier_consumes_the_event_bus(
    storage: SqliteStorage, sender: FakeSender, clock: FakeClock
) -> None:
    bus = EventBus(storage.events)
    notifier = PushNotifier(storage, bus, sender, clock)
    tv_id = await tv(storage)
    await subscribe(storage)
    await notifier.start()
    try:
        await bus.publish(tv_id, "pairing_lost", {"reason": "x"}, clock.now())
        for _ in range(200):
            if sender.sent:
                break
            await asyncio.sleep(0.01)
    finally:
        await notifier.stop()
    assert len(sender.sent) == 1


async def test_vapid_keys_are_created_once_and_kept(storage: SqliteStorage) -> None:
    first = await load_vapid_keys(storage.secrets)
    again = await load_vapid_keys(storage.secrets)
    assert first.public_key == again.public_key
    await storage.secrets.set("push_vapid_key", "garbage")
    assert (await load_vapid_keys(storage.secrets)).public_key != first.public_key
