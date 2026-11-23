"""The weekly report: how much each TV was watched last week, what, and how often it was blocked.

Pro only. The report is computed from the stored usage and events, so it can be asked for any
week still in the history; once a week, on Monday morning, it is published as one
``weekly_report`` event per TV for Web Push and Home Assistant.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from tvbalance.app.events import EventBus
from tvbalance.app.household import household_now
from tvbalance.ports.services import Clock, Entitlements
from tvbalance.ports.storage import Storage

log = logging.getLogger(__name__)

SENT_SETTING = "weekly_report_sent"  # the first day of the last week reported
SEND_AT = time(8, 0)  # local time on Monday
CHECK_EVERY = 600.0
TOP_CONTENT = 5
MAX_EVENTS = 20000


@dataclass(frozen=True, slots=True)
class ContentTotal:
    kind: str
    id: str
    seconds: int


@dataclass(frozen=True, slots=True)
class DayTotal:
    day: date
    seconds: int


@dataclass(frozen=True, slots=True)
class TvReport:
    tv_id: str
    tv_name: str
    total_seconds: int
    days: tuple[DayTotal, ...]  # oldest first, seven of them
    top_content: tuple[ContentTotal, ...]  # most viewed first
    blocks: int


@dataclass(frozen=True, slots=True)
class WeeklyReport:
    first: date  # a Monday
    last: date  # the Sunday after it
    tvs: tuple[TvReport, ...]


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def previous_week(today: date) -> date:
    """The Monday that starts the last complete week before ``today``."""
    return monday_of(today) - timedelta(days=7)


class ReportService:
    def __init__(
        self,
        storage: Storage,
        events: EventBus,
        clock: Clock,
        entitlements: Entitlements | None = None,
        interval: float = CHECK_EVERY,
    ) -> None:
        self._storage = storage
        self._events = events
        self._clock = clock
        self._entitlements = entitlements  # ``None``: nothing is gated
        self._interval = interval
        self._task: asyncio.Task[None] | None = None

    @property
    def effective(self) -> bool:
        return self._entitlements is None or self._entitlements.is_pro()

    async def build(self, week: date) -> WeeklyReport:
        """The report of the week that contains ``week``."""
        first = monday_of(week)
        last = first + timedelta(days=6)
        now = await household_now(self._storage.settings, self._clock)
        start = datetime.combine(first, time.min, tzinfo=now.tzinfo)
        end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=now.tzinfo)
        tvs = [
            await self._tv_report(tv.id, tv.name, first, last, start, end)
            for tv in await self._storage.tvs.list()
        ]
        return WeeklyReport(first, last, tuple(tvs))

    async def _tv_report(
        self, tv_id: str, name: str, first: date, last: date, start: datetime, end: datetime
    ) -> TvReport:
        days: list[DayTotal] = []
        for n in range(7):
            day = first + timedelta(days=n)
            days.append(DayTotal(day, (await self._storage.usage.get(tv_id, day)).watched_seconds))
        used = await self._storage.content_usage.between(tv_id, first, last)
        ranked = sorted(used.items(), key=lambda item: (-item[1], item[0].kind, item[0].id))
        stored = await self._storage.events.recent(tv_id, start, MAX_EVENTS)
        blocks = sum(1 for e in stored if e.type == "blocked" and e.occurred_at < end)
        return TvReport(
            tv_id=tv_id,
            tv_name=name,
            total_seconds=sum(d.seconds for d in days),
            days=tuple(days),
            top_content=tuple(ContentTotal(k.kind, k.id, s) for k, s in ranked[:TOP_CONTENT]),
            blocks=blocks,
        )

    async def publish_due(self) -> bool:
        """Publish last week's report when it is Monday morning and it has not gone out yet."""
        if not self.effective:
            return False
        now = await household_now(self._storage.settings, self._clock)
        if now.weekday() != 0 or now.time() < SEND_AT:
            return False
        week = previous_week(now.date())
        if await self._storage.settings.get(SENT_SETTING) == week.isoformat():
            return False
        await self._storage.settings.set(SENT_SETTING, week.isoformat())
        report = await self.build(week)
        for tv in report.tvs:
            payload = {
                "first": report.first.isoformat(),
                "last": report.last.isoformat(),
                "total_seconds": tv.total_seconds,
                "blocks": tv.blocks,
                "top": [{"kind": c.kind, "id": c.id, "seconds": c.seconds} for c in tv.top_content],
            }
            await self._events.publish(tv.tv_id, "weekly_report", payload, self._clock.now())
        return True

    async def run(self) -> None:
        while True:
            try:
                await self.publish_due()
            except Exception:
                log.exception("could not publish the weekly report")
            await asyncio.sleep(self._interval)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run(), name="weekly-report")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
