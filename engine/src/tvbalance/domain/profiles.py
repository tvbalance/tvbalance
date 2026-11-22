"""Profiles: which rule set applies to a TV right now. Pure functions, no I/O.

A profile is an existing rule set (a policy). It comes into force from a manual or automated
activation, or from a calendar entry; the most specific source wins.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

from tvbalance.domain.models import Schedule, TimeWindow
from tvbalance.domain.schedule import allowed_span


class ProfileSource(StrEnum):
    MANUAL = "manual"
    AUTOMATION = "automation"
    CALENDAR = "calendar"


@dataclass(frozen=True, slots=True)
class ProfileActivation:
    """A profile switched on by a person or an automation, from ``starts_at`` to ``ends_at``."""

    policy_id: int
    starts_at: datetime
    ends_at: datetime
    excluded_tv_ids: frozenset[str] = frozenset()
    source: ProfileSource = ProfileSource.MANUAL


@dataclass(frozen=True, slots=True)
class WeeklyEntry:
    """Every listed weekday (0 = Monday) from ``start`` to ``end``.

    Like a schedule window, ``start > end`` crosses midnight and belongs to the day it starts on,
    and ``start == end`` covers 24 hours.
    """

    policy_id: int
    weekdays: frozenset[int]
    start: time
    end: time
    excluded_tv_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class DatedEntry:
    """Whole local days from ``start_date`` to ``end_date``, both inclusive (a holiday)."""

    policy_id: int
    start_date: date
    end_date: date
    excluded_tv_ids: frozenset[str] = field(default_factory=frozenset)


type CalendarEntry = WeeklyEntry | DatedEntry


@dataclass(frozen=True, slots=True)
class ActiveProfile:
    policy_id: int
    until: datetime  # UTC
    source: ProfileSource


def _weekly_until(entry: WeeklyEntry, now: datetime) -> datetime | None:
    schedule = Schedule(
        windows={day: (TimeWindow(entry.start, entry.end),) for day in entry.weekdays}
    )
    span = allowed_span(schedule, now)
    return None if span is None else span.end


def _dated_until(entry: DatedEntry, now: datetime) -> datetime | None:
    if not entry.start_date <= now.date() <= entry.end_date:
        return None
    after = entry.end_date + timedelta(days=1)
    return datetime.combine(after, time.min, tzinfo=now.tzinfo).astimezone(UTC)


def resolve_profile(
    now: datetime,
    tv_id: str,
    activations: Sequence[ProfileActivation],
    entries: Sequence[CalendarEntry],
) -> ActiveProfile | None:
    """The profile in force for ``tv_id`` at ``now``, or ``None`` to keep the TV's own rules.

    ``now`` is timezone-aware and expressed in the household's zone. Precedence: the most
    recent activation in force, then a dated calendar entry (the latest start wins), then a
    weekly one (the first listed wins). A TV excluded by a source skips that source only.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    live = [
        a for a in activations if a.starts_at <= now < a.ends_at and tv_id not in a.excluded_tv_ids
    ]
    if live:
        chosen = max(live, key=lambda a: a.starts_at)
        return ActiveProfile(chosen.policy_id, chosen.ends_at.astimezone(UTC), chosen.source)

    dated = sorted(
        (e for e in entries if isinstance(e, DatedEntry) and tv_id not in e.excluded_tv_ids),
        key=lambda e: e.start_date,
        reverse=True,
    )
    for entry in dated:
        until = _dated_until(entry, now)
        if until is not None:
            return ActiveProfile(entry.policy_id, until, ProfileSource.CALENDAR)
    for weekly in entries:
        if isinstance(weekly, WeeklyEntry) and tv_id not in weekly.excluded_tv_ids:
            until = _weekly_until(weekly, now)
            if until is not None:
                return ActiveProfile(weekly.policy_id, until, ProfileSource.CALENDAR)
    return None
