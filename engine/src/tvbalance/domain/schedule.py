"""Allowed-time computation from a weekly schedule. Midnight and DST aware, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tvbalance.domain.models import Schedule, TimeWindow


@dataclass(frozen=True, slots=True)
class Span:
    """A continuous allowed interval, in UTC (start inclusive, end exclusive)."""

    start: datetime
    end: datetime


def _intervals(
    schedule: Schedule, day_offset: int, now: datetime
) -> list[tuple[datetime, datetime]]:
    day = now.date() + timedelta(days=day_offset)
    windows: tuple[TimeWindow, ...] = schedule.special_days.get(
        day, schedule.windows.get(day.weekday(), ())
    )
    tz = now.tzinfo
    result: list[tuple[datetime, datetime]] = []
    for window in windows:
        start = datetime.combine(day, window.start, tzinfo=tz)
        end_day = day if window.end > window.start else day + timedelta(days=1)
        end = datetime.combine(end_day, window.end, tzinfo=tz)
        # Compare in UTC: same-zone aware datetimes would otherwise compare by wall clock.
        result.append((start.astimezone(UTC), end.astimezone(UTC)))
    return result


def allowed_span(schedule: Schedule, now: datetime) -> Span | None:
    """The merged allowed interval containing ``now``, or ``None`` when viewing is not allowed.

    ``now`` must be timezone-aware and expressed in the household's zone: weekdays and
    special dates are read from its wall clock.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    instant = now.astimezone(UTC)
    intervals: list[tuple[datetime, datetime]] = []
    for offset in (-1, 0, 1):  # yesterday may spill past midnight; tomorrow may be adjacent
        intervals.extend(_intervals(schedule, offset, now))
    intervals.sort()

    merged: list[tuple[datetime, datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    for start, end in merged:
        if start <= instant < end:
            return Span(start, end)
    return None


def seconds_until_end(span: Span, now: datetime) -> int:
    """Whole seconds left in ``span`` (never negative)."""
    return max(0, int((span.end - now.astimezone(UTC)).total_seconds()))
