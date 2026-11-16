from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from tvbalance.domain.budget import accrue, remaining_seconds
from tvbalance.domain.models import Observation, Policy, Power, Usage

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
