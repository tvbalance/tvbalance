from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from tvbalance.domain.models import Schedule, TimeWindow
from tvbalance.domain.schedule import allowed_span, seconds_until_end

ROME = ZoneInfo("Europe/Rome")


def w(start: str, end: str) -> TimeWindow:
    return TimeWindow(time.fromisoformat(start), time.fromisoformat(end))


def at(day: str, clock: str, tz: ZoneInfo = ROME) -> datetime:
    return datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), tzinfo=tz)


# 2026-01-05 is a Monday.
WEEKDAY = Schedule(windows={0: (w("16:00", "20:00"),)})


def test_inside_window_returns_span() -> None:
    span = allowed_span(WEEKDAY, at("2026-01-05", "17:00"))
    assert span is not None
    assert span.end == at("2026-01-05", "20:00").astimezone(UTC)
    assert seconds_until_end(span, at("2026-01-05", "17:00")) == 3 * 3600


def test_start_inclusive_end_exclusive() -> None:
    assert allowed_span(WEEKDAY, at("2026-01-05", "16:00")) is not None
    assert allowed_span(WEEKDAY, at("2026-01-05", "20:00")) is None


def test_day_without_windows_is_blocked() -> None:
    assert allowed_span(WEEKDAY, at("2026-01-06", "17:00")) is None
    assert allowed_span(Schedule(), at("2026-01-05", "17:00")) is None


def test_window_crossing_midnight_belongs_to_starting_day() -> None:
    schedule = Schedule(windows={4: (w("20:00", "01:00"),)})  # Friday
    assert allowed_span(schedule, at("2026-01-09", "22:00")) is not None
    after = allowed_span(schedule, at("2026-01-10", "00:30"))  # Saturday small hours
    assert after is not None
    assert seconds_until_end(after, at("2026-01-10", "00:30")) == 30 * 60
    assert allowed_span(schedule, at("2026-01-10", "01:00")) is None
    # Saturday has no rule of its own: the tail of Friday's window is not repeated.
    assert allowed_span(schedule, at("2026-01-10", "22:00")) is None


def test_start_equals_end_covers_whole_day() -> None:
    schedule = Schedule(windows={0: (w("00:00", "00:00"),)})
    span = allowed_span(schedule, at("2026-01-05", "23:59"))
    assert span is not None
    assert seconds_until_end(span, at("2026-01-05", "23:59")) == 60


def test_adjacent_windows_across_midnight_merge() -> None:
    schedule = Schedule(windows={0: (w("20:00", "00:00"),), 1: (w("00:00", "07:00"),)})
    span = allowed_span(schedule, at("2026-01-05", "23:00"))
    assert span is not None
    assert seconds_until_end(span, at("2026-01-05", "23:00")) == 8 * 3600


def test_overlapping_and_adjacent_windows_in_a_day_merge() -> None:
    schedule = Schedule(
        windows={0: (w("10:00", "12:00"), w("11:00", "13:00"), w("13:00", "14:00"))}
    )
    span = allowed_span(schedule, at("2026-01-05", "10:30"))
    assert span is not None
    assert seconds_until_end(span, at("2026-01-05", "10:30")) == 3.5 * 3600


def test_gap_between_windows_is_blocked() -> None:
    schedule = Schedule(windows={0: (w("10:00", "12:00"), w("14:00", "16:00"))})
    assert allowed_span(schedule, at("2026-01-05", "13:00")) is None


def test_special_day_replaces_weekday_rule() -> None:
    schedule = Schedule(
        windows={0: (w("16:00", "20:00"),)},
        special_days={date(2026, 1, 5): (w("09:00", "12:00"),)},
    )
    assert allowed_span(schedule, at("2026-01-05", "17:00")) is None
    assert allowed_span(schedule, at("2026-01-05", "10:00")) is not None


def test_special_day_with_no_windows_blocks_the_date() -> None:
    schedule = Schedule(windows={0: (w("16:00", "20:00"),)}, special_days={date(2026, 1, 5): ()})
    assert allowed_span(schedule, at("2026-01-05", "17:00")) is None


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        allowed_span(WEEKDAY, datetime(2026, 1, 5, 17))


def test_spring_forward_window_is_one_hour_shorter() -> None:
    # Europe/Rome moved clocks forward on 2026-03-29 (02:00 -> 03:00).
    schedule = Schedule(windows={6: (w("01:00", "05:00"),)})  # Sunday
    start = at("2026-03-29", "01:30")
    span = allowed_span(schedule, start)
    assert span is not None
    assert seconds_until_end(span, start) == 2.5 * 3600  # 3.5 wall hours minus the skipped one


def test_fall_back_window_is_one_hour_longer() -> None:
    # Clocks went back on 2026-10-25 (03:00 -> 02:00).
    schedule = Schedule(windows={6: (w("01:00", "05:00"),)})
    start = at("2026-10-25", "01:30")
    span = allowed_span(schedule, start)
    assert span is not None
    assert seconds_until_end(span, start) == 4.5 * 3600
