from datetime import date, time

from tvbalance.domain.models import (
    AppTarget,
    ChannelTarget,
    HomeTarget,
    Policy,
    Schedule,
    TimeWindow,
)
from tvbalance.domain.validation import IssueCode, validate_policy


def codes(policy: Policy) -> list[IssueCode]:
    return [i.code for i in validate_policy(policy)]


def w(a: int, b: int) -> TimeWindow:
    return TimeWindow(time(a), time(b))


def test_default_policy_is_valid() -> None:
    assert codes(Policy()) == []


def test_fallback_checks() -> None:
    ok = Policy(fallback=ChannelTarget("n"), always_allowed_channels=frozenset({"n"}))
    assert codes(ok) == []
    assert codes(Policy(fallback=HomeTarget())) == []
    assert codes(Policy(fallback=ChannelTarget("n"))) == [IssueCode.FALLBACK_NOT_ALWAYS_ALLOWED]
    blocked = Policy(fallback=AppTarget("g"), blocked_apps=frozenset({"g"}))
    assert codes(blocked) == [IssueCode.FALLBACK_BLOCKED]
    not_listed = Policy(fallback=AppTarget("g"), allow_list_apps=frozenset({"k"}))
    assert codes(not_listed) == [IssueCode.FALLBACK_BLOCKED]


def test_conflicting_lists_name_the_kind() -> None:
    policy = Policy(always_allowed_apps=frozenset({"a"}), blocked_apps=frozenset({"a"}))
    assert validate_policy(policy)[0].detail == "apps"


def test_warn_thresholds_and_budget() -> None:
    assert codes(Policy(warn_at_minutes=(10, 0))) == [IssueCode.INVALID_WARN_THRESHOLD]
    assert codes(Policy(warn_at_minutes=(5, 5))) == [IssueCode.INVALID_WARN_THRESHOLD]
    assert codes(Policy(daily_budget_minutes=-1)) == [IssueCode.NEGATIVE_BUDGET]


def test_overlapping_windows_are_reported_but_adjacent_are_fine() -> None:
    assert codes(Policy(schedule=Schedule(windows={0: (w(8, 12), w(12, 14))}))) == []
    overlap = Schedule(windows={0: (w(8, 12), w(11, 14))})
    assert codes(Policy(schedule=overlap)) == [IssueCode.OVERLAPPING_WINDOWS]
    special = Schedule(special_days={date(2026, 1, 1): (w(20, 2), w(23, 3))})
    assert codes(Policy(schedule=special)) == [IssueCode.OVERLAPPING_WINDOWS]
