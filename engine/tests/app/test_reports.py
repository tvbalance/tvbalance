from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from support import FakeClock

from tvbalance.app.events import EventBus
from tvbalance.app.reports import ReportService, monday_of, previous_week
from tvbalance.config import EngineConfig
from tvbalance.domain.models import ContentKey
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage

MONDAY_MORNING = datetime(2026, 11, 23, 8, 30, tzinfo=UTC)  # 09:30 in Rome
LAST_WEEK = date(2026, 11, 16)


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
    await store.settings.set("timezone", "Europe/Rome")
    yield store
    await store.close()


async def seed(storage: Storage) -> str:
    tv = await storage.tvs.add("fake", "Living room", "tv.local", {})
    await storage.usage.add_watched(tv.id, LAST_WEEK, 3600)
    await storage.usage.add_watched(tv.id, LAST_WEEK + timedelta(days=2), 1800)
    await storage.usage.add_watched(tv.id, LAST_WEEK + timedelta(days=7), 999)  # this week
    content = storage.content_usage
    await content.add(tv.id, LAST_WEEK, ContentKey("app", "youtube"), 3000)
    await content.add(tv.id, LAST_WEEK + timedelta(days=2), ContentKey("app", "youtube"), 500)
    await content.add(tv.id, LAST_WEEK, ContentKey("input", "HDMI_1"), 1900)
    inside = datetime(2026, 11, 18, 17, 0, tzinfo=UTC)
    for at in (datetime(2026, 11, 15, 22, 0, tzinfo=UTC), inside, inside + timedelta(hours=1)):
        await storage.events.append(tv.id, "blocked", {"reason": "app_blocked"}, at)
    await storage.events.append(tv.id, "tv_paired", {}, inside)
    await storage.events.append(tv.id, "blocked", {}, datetime(2026, 11, 23, 7, 0, tzinfo=UTC))
    return tv.id


def test_weeks_start_on_monday() -> None:
    assert monday_of(date(2026, 11, 22)) == LAST_WEEK  # a Sunday
    assert monday_of(LAST_WEEK) == LAST_WEEK
    assert previous_week(date(2026, 11, 23)) == LAST_WEEK
    assert previous_week(date(2026, 11, 30)) == LAST_WEEK + timedelta(days=7)


async def test_the_report_adds_up_the_week(storage: Storage) -> None:
    tv_id = await seed(storage)
    service = ReportService(storage, EventBus(storage.events), FakeClock(MONDAY_MORNING))
    report = await service.build(date(2026, 11, 20))  # any day of the week will do
    assert (report.first, report.last) == (LAST_WEEK, date(2026, 11, 22))
    (tv,) = report.tvs
    assert (tv.tv_id, tv.tv_name, tv.total_seconds, tv.blocks) == (tv_id, "Living room", 5400, 2)
    assert [d.seconds for d in tv.days] == [3600, 0, 1800, 0, 0, 0, 0]
    assert [(c.kind, c.id, c.seconds) for c in tv.top_content] == [
        ("app", "youtube", 3500),
        ("input", "HDMI_1", 1900),
    ]


async def test_the_report_goes_out_once_on_monday_morning(storage: Storage) -> None:
    await seed(storage)
    clock = FakeClock(MONDAY_MORNING)
    bus = EventBus(storage.events)
    service = ReportService(storage, bus, clock, Plan(pro=True))
    async with bus.subscribe() as queue:
        assert await service.publish_due()
        assert not await service.publish_due()
        event = queue.get_nowait()
        assert queue.empty()
    assert event.type == "weekly_report" and event.tv_id is not None
    assert event.payload["first"] == "2026-11-16" and event.payload["last"] == "2026-11-22"
    assert event.payload["total_seconds"] == 5400 and event.payload["blocks"] == 2
    assert event.payload["top"][0] == {"kind": "app", "id": "youtube", "seconds": 3500}


async def test_the_report_waits_for_monday_8am_local(storage: Storage) -> None:
    await seed(storage)
    bus = EventBus(storage.events)
    early = FakeClock(datetime(2026, 11, 23, 6, 59, tzinfo=UTC))  # 07:59 in Rome
    assert not await ReportService(storage, bus, early, Plan(pro=True)).publish_due()
    tuesday = FakeClock(datetime(2026, 11, 24, 9, 0, tzinfo=UTC))
    assert not await ReportService(storage, bus, tuesday, Plan(pro=True)).publish_due()
    assert await ReportService(
        storage, bus, FakeClock(MONDAY_MORNING), Plan(pro=True)
    ).publish_due()


async def test_free_plan_gets_no_report(storage: Storage) -> None:
    await seed(storage)
    service = ReportService(
        storage, EventBus(storage.events), FakeClock(MONDAY_MORNING), Plan(False)
    )
    assert not service.effective
    assert not await service.publish_due()
