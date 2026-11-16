from datetime import timedelta

from domain_helpers import at, tv

from tvbalance.domain.enforcement import EnforcementState, StepResult, step
from tvbalance.domain.models import (
    Allow,
    AppTarget,
    Block,
    Blocked,
    BlockReason,
    EnforcementPaused,
    EnforcementUnavailable,
    GoHome,
    LaunchApp,
    LimitKind,
    MessageKind,
    Policy,
    Power,
    PoweredOff,
    PowerOff,
    Redirected,
    ShowMessage,
    TimeWarning,
    Warn,
)
from tvbalance.sdk.types import Capability as C

ALL = set(C)
TIME_UP = Block(BlockReason.OUTSIDE_WINDOW)
APP = Block(BlockReason.APP_BLOCKED)
T0 = at("21:00")


def s(sec: int):  # type: ignore[no-untyped-def]
    return T0 + timedelta(seconds=sec)


def run(state, sec, decision, caps=ALL, policy=None, power=Power.ON):  # type: ignore[no-untyped-def]
    return step(state, s(sec), decision, tv(power), caps, policy or Policy())


def drive(decision, seconds, caps=ALL, policy=None):  # type: ignore[no-untyped-def]
    """Step once per second; return (final state, [(second, StepResult)] for non-empty steps)."""
    state, log = EnforcementState(), []
    for sec in seconds:
        result: StepResult = run(state, sec, decision, caps, policy)
        state = result.state
        if result.actions or result.events:
            log.append((sec, result))
    return state, log


def test_warning_fires_once_per_threshold() -> None:
    state = EnforcementState()
    first = run(state, 0, Warn(10, LimitKind.WINDOW))
    assert first.actions == (ShowMessage(MessageKind.TIME_WARNING, 10),)
    assert first.events == (TimeWarning(10, LimitKind.WINDOW),)
    again = run(first.state, 5, Warn(9, LimitKind.WINDOW))
    assert again.actions == () and again.events == ()
    second = run(again.state, 300, Warn(5, LimitKind.WINDOW))
    assert second.events == (TimeWarning(5, LimitKind.WINDOW),)


def test_first_warning_below_every_threshold_fires_once() -> None:
    first = run(EnforcementState(), 0, Warn(3, LimitKind.BUDGET))
    assert first.events == (TimeWarning(3, LimitKind.BUDGET),)
    assert run(first.state, 1, Warn(3, LimitKind.BUDGET)).events == ()


def test_bonus_rearms_thresholds() -> None:
    state = run(EnforcementState(), 0, Warn(5, LimitKind.BUDGET)).state
    state = run(state, 10, Warn(9, LimitKind.BUDGET)).state  # bonus lifted the clock to 9 min
    again = run(state, 20, Warn(5, LimitKind.BUDGET))
    assert again.events == (TimeWarning(5, LimitKind.BUDGET),)


def test_new_day_clears_warnings() -> None:
    state = run(EnforcementState(), 0, Warn(5, LimitKind.BUDGET)).state
    next_day = step(state, T0 + timedelta(days=1), Warn(5, LimitKind.BUDGET), tv(), ALL, Policy())
    assert next_day.events == (TimeWarning(5, LimitKind.BUDGET),)


def test_allow_and_tv_off_end_the_episode() -> None:
    started = run(EnforcementState(), 0, TIME_UP).state
    assert started.episode_started is not None
    assert run(started, 1, Allow()).state.episode_started is None
    assert run(started, 1, TIME_UP, power=Power.STANDBY).state.episode_started is None


def test_nothing_happens_before_debounce() -> None:
    _, log = drive(TIME_UP, range(0, 3))
    assert log == []


def test_time_limit_ladder_notify_then_power_off() -> None:
    _, log = drive(TIME_UP, range(0, 20))
    assert [sec for sec, _ in log] == [3, 18]
    assert log[0][1].actions == (ShowMessage(MessageKind.TIME_UP),)
    assert log[0][1].events == (Blocked(BlockReason.OUTSIDE_WINDOW),)
    assert log[1][1].actions == (PowerOff(),)
    assert log[1][1].events == (PoweredOff(),)


def test_time_limit_redirects_to_exempt_fallback_before_power_off() -> None:
    policy = Policy(fallback=AppTarget("news"), always_allowed_apps=frozenset({"news"}))
    _, log = drive(TIME_UP, range(0, 35), policy=policy)
    assert [sec for sec, _ in log] == [3, 18, 33]
    assert log[1][1].actions == (LaunchApp("news"),)
    assert log[1][1].events == (Redirected(LaunchApp("news")),)
    assert log[2][1].actions == (PowerOff(),)


def test_blocked_content_is_redirected_immediately_then_powered_off() -> None:
    _, log = drive(APP, range(0, 20))
    assert [sec for sec, _ in log] == [3, 18]
    assert log[0][1].actions == (ShowMessage(MessageKind.CONTENT_BLOCKED), GoHome())
    assert log[1][1].actions == (PowerOff(),)


def test_one_redirect_per_episode() -> None:
    _, log = drive(APP, range(0, 200), caps={C.GO_HOME, C.ON_SCREEN_MESSAGE})
    redirects = [r for _, r in log for e in r.events if isinstance(e, Redirected)]
    assert len(redirects) == 1


def test_power_off_cap_pauses_enforcement() -> None:
    state, offs, paused = EnforcementState(), 0, None
    for sec in range(0, 200):
        result = run(state, sec, TIME_UP)
        state = result.state
        offs += sum(isinstance(a, PowerOff) for a in result.actions)
        for e in result.events:
            if isinstance(e, EnforcementPaused):
                paused = (sec, e)
    assert offs == 3
    assert paused is not None
    assert paused[1].until == s(paused[0]) + timedelta(minutes=10)
    assert run(state, 201, TIME_UP).actions == ()  # still paused
    after = run(state, paused[0] + 601, TIME_UP)
    assert after.state.paused_until is None


def test_unavailable_when_tv_cannot_power_off_reports_once_and_repeats_message() -> None:
    caps = {C.ON_SCREEN_MESSAGE}
    _, log = drive(TIME_UP, range(0, 200), caps=caps)
    unavailable = [
        r for _, r in log if any(isinstance(e, EnforcementUnavailable) for e in r.events)
    ]
    assert len(unavailable) == 1
    messages = [sec for sec, r in log if r.actions]
    assert messages == [3, 63, 123, 183]
