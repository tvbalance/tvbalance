from datetime import timedelta

from domain_helpers import DAY, always_open, at, tv, window

from tvbalance.domain.models import (
    Allow,
    AppBudget,
    Block,
    BlockReason,
    LimitKind,
    Override,
    Policy,
    Power,
    Usage,
    Warn,
)
from tvbalance.domain.rules import evaluate

OPEN = Policy(schedule=always_open())


def block_override(now_clock: str = "18:00", minutes: int = 30) -> Override:
    return Override(
        allow=False, until=at(now_clock) + timedelta(minutes=minutes), created_at=at("17:00")
    )


def allow_override(until: str, created: str = "17:00") -> Override:
    return Override(allow=True, until=at(until), created_at=at(created))


def test_tv_not_on_is_always_allowed() -> None:
    for power in (Power.STANDBY, Power.OFF):
        assert evaluate(at("03:00"), tv(power), Policy(), Usage(DAY)) == Allow()
        assert evaluate(at("18:00"), tv(power), OPEN, Usage(DAY), (block_override(),)) == Allow()


def test_inside_window_without_limits_is_allowed() -> None:
    assert evaluate(at("18:00"), tv(), OPEN, Usage(DAY)) == Allow()


def test_outside_window_blocks() -> None:
    policy = Policy(schedule=window("16:00", "20:00"))
    assert evaluate(at("21:00"), tv(), policy, Usage(DAY)) == Block(BlockReason.OUTSIDE_WINDOW)


def test_empty_schedule_blocks_all_day() -> None:
    assert evaluate(at("12:00"), tv(), Policy(), Usage(DAY)) == Block(BlockReason.OUTSIDE_WINDOW)


def test_budget_exhausted_blocks_and_bonus_unblocks() -> None:
    policy = Policy(schedule=always_open(), daily_budget_minutes=60)
    spent = Usage(DAY, watched_seconds=3600)
    assert evaluate(at("18:00"), tv(), policy, spent) == Block(BlockReason.BUDGET_EXHAUSTED)
    bonus = Usage(DAY, watched_seconds=3600, bonus_minutes=30)
    assert evaluate(at("18:00"), tv(), policy, bonus) == Allow()
    nearly = Usage(DAY, watched_seconds=3600, bonus_minutes=5)
    assert evaluate(at("18:00"), tv(), policy, nearly) == Warn(5, LimitKind.BUDGET)


def test_window_end_warns_when_inside_threshold() -> None:
    policy = Policy(schedule=window("16:00", "20:00"))
    assert evaluate(at("19:49"), tv(), policy, Usage(DAY)) == Allow()
    assert evaluate(at("19:50"), tv(), policy, Usage(DAY)) == Warn(10, LimitKind.WINDOW)
    assert evaluate(at("19:55"), tv(), policy, Usage(DAY)) == Warn(5, LimitKind.WINDOW)


def test_partial_minutes_round_up() -> None:
    policy = Policy(schedule=window("16:00", "20:00"))
    assert evaluate(at("19:55:30"), tv(), policy, Usage(DAY)) == Warn(5, LimitKind.WINDOW)


def test_the_nearest_limit_wins_the_warning() -> None:
    policy = Policy(schedule=window("16:00", "20:00"), daily_budget_minutes=60)
    usage = Usage(DAY, watched_seconds=57 * 60)
    assert evaluate(at("19:55"), tv(), policy, usage) == Warn(3, LimitKind.BUDGET)


def test_no_warning_thresholds_means_no_warn() -> None:
    policy = Policy(schedule=window("16:00", "20:00"), warn_at_minutes=())
    assert evaluate(at("19:59"), tv(), policy, Usage(DAY)) == Allow()


def test_blocked_app_input_and_channel() -> None:
    policy = Policy(
        schedule=always_open(),
        blocked_apps=frozenset({"games"}),
        blocked_inputs=frozenset({"hdmi2"}),
        blocked_channels=frozenset({"c9"}),
    )
    assert evaluate(at("18:00"), tv(foreground_app="games"), policy, Usage(DAY)) == Block(
        BlockReason.APP_BLOCKED
    )
    assert evaluate(at("18:00"), tv(input_id="hdmi2"), policy, Usage(DAY)) == Block(
        BlockReason.INPUT_BLOCKED
    )
    assert evaluate(at("18:00"), tv(channel_id="c9"), policy, Usage(DAY)) == Block(
        BlockReason.CHANNEL_BLOCKED
    )
    assert evaluate(at("18:00"), tv(foreground_app="video"), policy, Usage(DAY)) == Allow()


def test_allow_list_blocks_everything_else() -> None:
    policy = Policy(schedule=always_open(), allow_list_apps=frozenset({"kids"}))
    assert evaluate(at("18:00"), tv(foreground_app="kids"), policy, Usage(DAY)) == Allow()
    assert evaluate(at("18:00"), tv(foreground_app="other"), policy, Usage(DAY)) == Block(
        BlockReason.APP_BLOCKED
    )


def test_time_limit_takes_precedence_over_content_block() -> None:
    policy = Policy(blocked_apps=frozenset({"games"}))  # empty schedule
    obs = tv(foreground_app="games")
    assert evaluate(at("18:00"), obs, policy, Usage(DAY)) == Block(BlockReason.OUTSIDE_WINDOW)


def test_always_allowed_content_ignores_time_limits() -> None:
    policy = Policy(always_allowed_channels=frozenset({"news"}))  # empty schedule
    assert evaluate(at("23:00"), tv(channel_id="news"), policy, Usage(DAY)) == Allow()


def test_block_override_blocks_everything_even_always_allowed() -> None:
    policy = Policy(schedule=always_open(), always_allowed_channels=frozenset({"news"}))
    result = evaluate(at("18:00"), tv(channel_id="news"), policy, Usage(DAY), (block_override(),))
    assert result == Block(BlockReason.OVERRIDE)


def test_expired_or_future_override_is_ignored() -> None:
    expired = Override(allow=False, until=at("17:30"), created_at=at("17:00"))
    future = Override(allow=False, until=at("19:00"), created_at=at("18:30"))
    assert evaluate(at("18:00"), tv(), OPEN, Usage(DAY), (expired, future)) == Allow()


def test_allow_override_lifts_time_limits_and_warns_on_its_end() -> None:
    policy = Policy(daily_budget_minutes=60)  # empty schedule + spent budget
    spent = Usage(DAY, watched_seconds=7200)
    assert evaluate(at("21:00"), tv(), policy, spent) == Block(BlockReason.OUTSIDE_WINDOW)
    result = evaluate(at("21:00"), tv(), policy, spent, (allow_override("21:30"),))
    assert result == Allow()
    near_end = evaluate(at("21:25"), tv(), policy, spent, (allow_override("21:30"),))
    assert near_end == Warn(5, LimitKind.OVERRIDE)


def test_allow_override_does_not_lift_content_blocks() -> None:
    policy = Policy(schedule=always_open(), blocked_apps=frozenset({"games"}))
    result = evaluate(
        at("18:00"), tv(foreground_app="games"), policy, Usage(DAY), (allow_override("19:00"),)
    )
    assert result == Block(BlockReason.APP_BLOCKED)


def test_most_recent_active_override_wins() -> None:
    older_block = Override(allow=False, until=at("19:00"), created_at=at("17:00"))
    newer_allow = Override(allow=True, until=at("19:00"), created_at=at("17:30"))
    assert evaluate(at("18:00"), tv(), Policy(), Usage(DAY), (older_block, newer_allow)) == Allow()
    newer_block = Override(allow=False, until=at("19:00"), created_at=at("17:45"))
    result = evaluate(at("18:00"), tv(), OPEN, Usage(DAY), (newer_allow, newer_block))
    assert result == Block(BlockReason.OVERRIDE)


GAMES = Policy(schedule=always_open(), app_budgets=(AppBudget("games", frozenset({"a", "b"}), 30),))


def test_an_exhausted_app_group_blocks_its_apps_only() -> None:
    used = {"a": 1000, "b": 800}
    assert evaluate(
        at("18:00"), tv(foreground_app="a"), GAMES, Usage(DAY), app_seconds=used
    ) == Block(BlockReason.APP_BUDGET_EXHAUSTED)
    assert (
        evaluate(at("18:00"), tv(foreground_app="z"), GAMES, Usage(DAY), app_seconds=used)
        == Allow()
    )


def test_an_app_group_warns_before_it_runs_out() -> None:
    used = {"a": 25 * 60}
    assert evaluate(
        at("18:00"), tv(foreground_app="b"), GAMES, Usage(DAY), app_seconds=used
    ) == Warn(5, LimitKind.APP_BUDGET)


def test_an_allow_override_lifts_the_app_group_limit() -> None:
    used = {"a": 99999}
    decision = evaluate(
        at("18:00"),
        tv(foreground_app="a"),
        GAMES,
        Usage(DAY),
        (allow_override("20:00"),),
        app_seconds=used,
    )
    assert decision == Allow()


def test_rollover_postpones_the_budget_block() -> None:
    policy = Policy(schedule=always_open(), daily_budget_minutes=60)
    spent = Usage(DAY, watched_seconds=3600)
    assert evaluate(at("18:00"), tv(), policy, spent) == Block(BlockReason.BUDGET_EXHAUSTED)
    assert evaluate(at("18:00"), tv(), policy, spent, rollover=20) == Allow()
