from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from tvbalance.domain.budget import (
    accrue,
    app_budget_left,
    base_policy,
    remaining_seconds,
    rollover_minutes,
)
from tvbalance.domain.models import AppBudget, Observation, Policy, Power, Usage

ROME = ZoneInfo("Europe/Rome")
DAY = date(2026, 1, 5)
NOW = datetime(2026, 1, 5, 18, 0, tzinfo=ROME)


def obs(power: Power = Power.ON, **kw: str) -> Observation:
    return Observation(observed_at=NOW, power=power, **kw)


def test_no_budget_means_unlimited() -> None:
    assert remaining_seconds(Policy(), Usage(DAY, watched_seconds=9999)) is None


def test_remaining_includes_bonus_and_never_goes_negative() -> None:
    policy = Policy(daily_budget_minutes=60)
    assert remaining_seconds(policy, Usage(DAY, 1800)) == 1800
    assert remaining_seconds(policy, Usage(DAY, 3600, bonus_minutes=15)) == 900
    assert remaining_seconds(policy, Usage(DAY, 99999)) == 0


def test_accrues_elapsed_time_while_on() -> None:
    policy = Policy(daily_budget_minutes=60)
    out = accrue(Usage(DAY), NOW - timedelta(seconds=5), NOW, obs(), policy)
    assert out.watched_seconds == 5


def test_standby_and_off_do_not_accrue() -> None:
    policy = Policy(daily_budget_minutes=60)
    for power in (Power.STANDBY, Power.OFF):
        out = accrue(Usage(DAY), NOW - timedelta(seconds=5), NOW, obs(power), policy)
        assert out.watched_seconds == 0


def test_always_allowed_content_does_not_accrue() -> None:
    policy = Policy(daily_budget_minutes=60, always_allowed_channels=frozenset({"news"}))
    out = accrue(Usage(DAY), NOW - timedelta(seconds=5), NOW, obs(channel_id="news"), policy)
    assert out.watched_seconds == 0


def test_long_gap_is_capped() -> None:
    out = accrue(Usage(DAY), NOW - timedelta(hours=2), NOW, obs(), Policy())
    assert out.watched_seconds == 120


def test_negative_or_zero_elapsed_is_ignored() -> None:
    out = accrue(Usage(DAY, 10), NOW + timedelta(seconds=5), NOW, obs(), Policy())
    assert out.watched_seconds == 10


def test_new_day_resets_usage_and_bonus() -> None:
    yesterday = Usage(date(2026, 1, 4), watched_seconds=5000, bonus_minutes=30)
    out = accrue(yesterday, NOW - timedelta(seconds=5), NOW, obs(), Policy())
    assert out == Usage(DAY, watched_seconds=5)


def test_time_before_midnight_is_not_billed_to_the_new_day() -> None:
    just_after = datetime(2026, 1, 6, 0, 0, 10, tzinfo=ROME)
    before = datetime(2026, 1, 5, 23, 59, 50, tzinfo=ROME)
    out = accrue(Usage(DAY, 100), before, just_after, obs(), Policy())
    assert out == Usage(date(2026, 1, 6), watched_seconds=10)


def test_mixed_timezones_are_compared_as_instants() -> None:
    last = (NOW - timedelta(seconds=5)).astimezone(UTC)
    assert accrue(Usage(DAY), last, NOW, obs(), Policy()).watched_seconds == 5


def test_a_weekday_budget_replaces_the_general_one_for_that_day() -> None:
    policy = Policy(daily_budget_minutes=60, weekday_budget_minutes={0: 120})  # DAY is a Monday
    assert remaining_seconds(policy, Usage(DAY)) == 7200
    assert remaining_seconds(policy, Usage(DAY + timedelta(days=1))) == 3600


def test_a_weekday_budget_works_without_a_general_one() -> None:
    policy = Policy(weekday_budget_minutes={0: 30})
    assert remaining_seconds(policy, Usage(DAY)) == 1800
    assert remaining_seconds(policy, Usage(DAY + timedelta(days=1))) is None


def test_rollover_adds_to_the_day_budget() -> None:
    assert remaining_seconds(Policy(daily_budget_minutes=60), Usage(DAY, 600), rollover=20) == 4200


def test_rollover_carries_unused_minutes_up_to_the_cap() -> None:
    policy = Policy(daily_budget_minutes=60, rollover_max_minutes=30)
    assert rollover_minutes(policy, Usage(DAY, 40 * 60)) == 20
    assert rollover_minutes(policy, Usage(DAY, 0)) == 30
    assert rollover_minutes(policy, Usage(DAY, 99999)) == 0


def test_rollover_counts_yesterdays_bonus_and_weekday_budget() -> None:
    policy = Policy(
        daily_budget_minutes=60, weekday_budget_minutes={0: 90}, rollover_max_minutes=200
    )
    assert rollover_minutes(policy, Usage(DAY, 60 * 60, bonus_minutes=10)) == 40


def test_rollover_is_off_without_a_cap_or_a_budget() -> None:
    assert rollover_minutes(Policy(daily_budget_minutes=60), Usage(DAY)) == 0
    assert rollover_minutes(Policy(rollover_max_minutes=30), Usage(DAY)) == 0


def test_app_budget_left_sums_the_group() -> None:
    policy = Policy(app_budgets=(AppBudget("games", frozenset({"a", "b"}), 10),))
    assert app_budget_left(policy, "a", {"a": 120, "b": 60, "c": 500}) == 420
    assert app_budget_left(policy, "b", {"a": 9999}) == 0
    assert app_budget_left(policy, "c", {}) is None
    assert app_budget_left(policy, None, {}) is None


def test_base_policy_drops_only_the_advanced_budgets() -> None:
    policy = Policy(
        daily_budget_minutes=60,
        weekday_budget_minutes={0: 90},
        app_budgets=(AppBudget("games", frozenset({"a"}), 10),),
        rollover_max_minutes=30,
    )
    assert base_policy(policy) == Policy(daily_budget_minutes=60)
