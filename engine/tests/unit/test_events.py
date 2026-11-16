import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tvbalance.app.events import BusEvent, EventBus, to_record
from tvbalance.domain.models import (
    Blocked,
    BlockReason,
    EnforcementPaused,
    EnforcementUnavailable,
    GoHome,
    LaunchApp,
    LimitKind,
    PoweredOff,
    Redirected,
    TimeWarning,
)

AT = datetime(2026, 11, 17, 18, 0, tzinfo=UTC)


class MemoryLog:
    def __init__(self, *, fail: bool = False) -> None:
        self.rows: list[tuple[str | None, str, dict[str, Any], datetime]] = []
        self.fail = fail

    async def append(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None:
        if self.fail:
            raise OSError("disk full")
        self.rows.append((tv_id, event_type, payload, at))


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (
            TimeWarning(5, LimitKind.BUDGET),
            ("time_warning", {"minutes_left": 5, "limit": "budget"}),
        ),
        (Blocked(BlockReason.APP_BLOCKED), ("blocked", {"reason": "app_blocked"})),
        (Redirected(GoHome()), ("redirected", {"action": {"kind": "go_home"}})),
        (
            Redirected(LaunchApp("news")),
            ("redirected", {"action": {"kind": "launch_app", "app_id": "news"}}),
        ),
        (PoweredOff(), ("powered_off", {})),
        (
            EnforcementPaused(AT),
            ("enforcement_paused", {"until": "2026-11-17T18:00:00+00:00"}),
        ),
        (
            EnforcementUnavailable(BlockReason.BUDGET_EXHAUSTED),
            ("enforcement_unavailable", {"reason": "budget_exhausted"}),
        ),
    ],
)
def test_domain_events_become_records(event: Any, expected: tuple[str, dict[str, Any]]) -> None:
    assert to_record(event) == expected


async def test_publish_stores_then_fans_out() -> None:
    log = MemoryLog()
    bus = EventBus(log)
    async with bus.subscribe() as queue:
        await bus.publish("tv1", "blocked", {"reason": "app_blocked"}, AT)
        event = queue.get_nowait()
    assert log.rows == [("tv1", "blocked", {"reason": "app_blocked"}, AT)]
    assert event == BusEvent("tv1", "blocked", {"reason": "app_blocked"}, AT)


async def test_every_subscriber_gets_every_event() -> None:
    bus = EventBus(MemoryLog())
    async with bus.subscribe() as first, bus.subscribe() as second:
        await bus.publish("tv1", "powered_off", {}, AT)
        assert first.get_nowait() == second.get_nowait()


async def test_unsubscribed_queue_stops_receiving() -> None:
    bus = EventBus(MemoryLog())
    async with bus.subscribe() as queue:
        pass
    await bus.publish("tv1", "powered_off", {}, AT)
    assert queue.empty()


async def test_slow_subscriber_loses_its_oldest_events_without_blocking() -> None:
    bus = EventBus(MemoryLog(), queue_size=3)
    async with bus.subscribe() as queue:
        for minute in range(5):
            await bus.publish("tv1", "time_warning", {"n": minute}, AT + timedelta(minutes=minute))
        kept = [queue.get_nowait().payload["n"] for _ in range(queue.qsize())]
    assert kept == [2, 3, 4]


async def test_failing_log_write_is_reported_but_events_still_fan_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    bus = EventBus(MemoryLog(fail=True))
    with caplog.at_level(logging.ERROR):
        async with bus.subscribe() as queue:
            await bus.publish("tv1", "blocked", {}, AT)
            assert queue.get_nowait().type == "blocked"
    assert "disk full" in caplog.text
