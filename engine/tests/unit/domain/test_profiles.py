from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from tvbalance.domain.profiles import (
    ActiveProfile,
    DatedEntry,
    ProfileActivation,
    ProfileSource,
    WeeklyEntry,
    resolve_profile,
)

ROME = ZoneInfo("Europe/Rome")


def at(day: str, clock: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), tzinfo=ROME)


def manual(
    policy_id: int,
    start: datetime,
    end: datetime,
    excluded: frozenset[str] = frozenset(),
    source: ProfileSource = ProfileSource.MANUAL,
) -> ProfileActivation:
    return ProfileActivation(policy_id, start, end, excluded, source)


# 2026-01-05 is a Monday.
NOW = at("2026-01-05", "17:00")


def test_nothing_configured_resolves_to_no_profile() -> None:
    assert resolve_profile(NOW, "tv", (), ()) is None


def test_a_manual_activation_in_force_wins() -> None:
    found = resolve_profile(
        NOW, "tv", (manual(7, at("2026-01-05", "16:00"), at("2026-01-06", "00:00")),), ()
    )
    assert found == ActiveProfile(
        7, at("2026-01-06", "00:00").astimezone(UTC), ProfileSource.MANUAL
    )


def test_an_expired_or_future_activation_is_ignored() -> None:
    past = manual(1, at("2026-01-04", "10:00"), at("2026-01-05", "16:59"))
    future = manual(2, at("2026-01-05", "17:01"), at("2026-01-05", "18:00"))
    assert resolve_profile(NOW, "tv", (past, future), ()) is None


def test_the_end_instant_is_exclusive() -> None:
    activation = manual(1, at("2026-01-05", "16:00"), NOW)
    assert resolve_profile(NOW, "tv", (activation,), ()) is None


def test_the_most_recent_activation_wins() -> None:
    older = manual(1, at("2026-01-05", "10:00"), at("2026-01-06", "10:00"))
    newer = manual(2, at("2026-01-05", "16:00"), at("2026-01-05", "18:00"))
    found = resolve_profile(NOW, "tv", (older, newer), ())
    assert found is not None and found.policy_id == 2


def test_an_excluded_tv_gets_no_profile_but_the_others_do() -> None:
    activation = manual(
        3, at("2026-01-05", "16:00"), at("2026-01-05", "18:00"), frozenset({"parents"})
    )
    assert resolve_profile(NOW, "parents", (activation,), ()) is None
    assert resolve_profile(NOW, "kids", (activation,), ()) is not None


def test_an_automation_keeps_its_source() -> None:
    activation = manual(
        3, at("2026-01-05", "16:00"), at("2026-01-05", "18:00"), source=ProfileSource.AUTOMATION
    )
    found = resolve_profile(NOW, "tv", (activation,), ())
    assert found is not None and found.source is ProfileSource.AUTOMATION


def test_a_weekly_entry_applies_inside_its_window_until_its_end() -> None:
    entry = WeeklyEntry(5, frozenset({0}), time(16), time(20))
    found = resolve_profile(NOW, "tv", (), (entry,))
    assert found == ActiveProfile(
        5, at("2026-01-05", "20:00").astimezone(UTC), ProfileSource.CALENDAR
    )


def test_a_weekly_entry_does_not_apply_on_other_days_or_outside_the_window() -> None:
    entry = WeeklyEntry(5, frozenset({0}), time(16), time(20))
    assert resolve_profile(at("2026-01-06", "17:00"), "tv", (), (entry,)) is None
    assert resolve_profile(at("2026-01-05", "20:00"), "tv", (), (entry,)) is None
    assert resolve_profile(at("2026-01-05", "15:59"), "tv", (), (entry,)) is None


def test_a_weekly_entry_crossing_midnight_belongs_to_its_starting_day() -> None:
    entry = WeeklyEntry(5, frozenset({4}), time(22), time(6))  # Friday night
    friday_night = resolve_profile(at("2026-01-09", "23:00"), "tv", (), (entry,))
    saturday_early = resolve_profile(at("2026-01-10", "05:00"), "tv", (), (entry,))
    saturday_evening = resolve_profile(at("2026-01-10", "23:00"), "tv", (), (entry,))
    assert friday_night is not None
    assert saturday_early is not None
    assert saturday_early.until == at("2026-01-10", "06:00").astimezone(UTC)
    assert saturday_evening is None


def test_equal_start_and_end_cover_the_whole_day() -> None:
    entry = WeeklyEntry(5, frozenset({0}), time(0), time(0))
    assert resolve_profile(at("2026-01-05", "03:00"), "tv", (), (entry,)) is not None


def test_a_dated_entry_covers_whole_days_inclusive() -> None:
    entry = DatedEntry(6, date(2026, 1, 5), date(2026, 1, 7))
    first = resolve_profile(at("2026-01-05", "00:00"), "tv", (), (entry,))
    last = resolve_profile(at("2026-01-07", "23:59"), "tv", (), (entry,))
    assert first is not None and first.policy_id == 6
    assert last is not None and last.until == at("2026-01-08", "00:00").astimezone(UTC)
    assert resolve_profile(at("2026-01-08", "00:00"), "tv", (), (entry,)) is None
    assert resolve_profile(at("2026-01-04", "23:59"), "tv", (), (entry,)) is None


def test_a_dated_entry_beats_a_weekly_one_and_a_manual_activation_beats_both() -> None:
    weekly = WeeklyEntry(5, frozenset({0}), time(0), time(0))
    dated = DatedEntry(6, date(2026, 1, 5), date(2026, 1, 5))
    chosen = resolve_profile(NOW, "tv", (), (weekly, dated))
    assert chosen is not None and chosen.policy_id == 6
    activation = manual(7, at("2026-01-05", "16:00"), at("2026-01-05", "18:00"))
    chosen = resolve_profile(NOW, "tv", (activation,), (weekly, dated))
    assert chosen is not None and chosen.policy_id == 7


def test_among_dated_entries_the_latest_start_wins() -> None:
    broad = DatedEntry(1, date(2026, 1, 1), date(2026, 1, 31))
    narrow = DatedEntry(2, date(2026, 1, 5), date(2026, 1, 6))
    chosen = resolve_profile(NOW, "tv", (), (broad, narrow))
    assert chosen is not None and chosen.policy_id == 2


def test_calendar_entries_can_exclude_a_tv() -> None:
    entry = DatedEntry(6, date(2026, 1, 5), date(2026, 1, 5), frozenset({"parents"}))
    assert resolve_profile(NOW, "parents", (), (entry,)) is None
    assert resolve_profile(NOW, "kids", (), (entry,)) is not None


def test_an_excluded_tv_falls_through_to_the_next_source() -> None:
    dated = DatedEntry(6, date(2026, 1, 5), date(2026, 1, 5), frozenset({"tv"}))
    weekly = WeeklyEntry(5, frozenset({0}), time(0), time(0))
    chosen = resolve_profile(NOW, "tv", (), (dated, weekly))
    assert chosen is not None and chosen.policy_id == 5


def test_a_dst_day_ends_at_the_next_local_midnight() -> None:
    entry = DatedEntry(6, date(2026, 3, 29), date(2026, 3, 29))  # clocks go forward in Rome
    found = resolve_profile(at("2026-03-29", "12:00"), "tv", (), (entry,))
    assert found is not None
    assert found.until == datetime(2026, 3, 29, 22, 0, tzinfo=UTC)
    assert found.until - at("2026-03-29", "00:00").astimezone(UTC) == timedelta(hours=23)
