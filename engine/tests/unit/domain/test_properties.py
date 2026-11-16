from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given, settings
from hypothesis import strategies as st

from tvbalance.domain.enforcement import EnforcementState, step
from tvbalance.domain.models import (
    Allow,
    Block,
    BlockReason,
    Decision,
    EnforcementLevel,
    GoHome,
    LaunchApp,
    LimitKind,
    Observation,
    Override,
    Policy,
    Power,
    PowerOff,
    Redirected,
    Schedule,
    SetChannel,
    SetInput,
    ShowMessage,
    TimeWindow,
    Usage,
    Warn,
)
from tvbalance.domain.rules import evaluate, plan_actions
from tvbalance.sdk.types import Capability

ROME = ZoneInfo("Europe/Rome")

instants = st.datetimes(
    min_value=datetime(2026, 1, 1), max_value=datetime(2026, 12, 31), timezones=st.just(ROME)
)
times = st.builds(time, st.integers(0, 23), st.integers(0, 59))
windows = st.builds(TimeWindow, times, times)
schedules = st.builds(
    Schedule,
    windows=st.dictionaries(st.integers(0, 6), st.lists(windows, max_size=3).map(tuple)),
)
policies = st.builds(
    Policy,
    schedule=schedules,
    daily_budget_minutes=st.none() | st.integers(0, 600),
    warn_at_minutes=st.lists(st.integers(1, 30), unique=True, max_size=3).map(tuple),
)
powers = st.sampled_from(Power)
observations = st.builds(Observation, observed_at=instants, power=powers)
usages = st.builds(
    Usage,
    day=instants.map(lambda d: d.date()),
    watched_seconds=st.integers(0, 40_000),
    bonus_minutes=st.integers(0, 120),
)


@given(instants, observations, policies, usages)
def test_tv_not_on_is_always_allowed(now, obs, policy, usage) -> None:  # type: ignore[no-untyped-def]
    if obs.power is not Power.ON:
        assert evaluate(now, obs, policy, usage) == Allow()


@given(instants, policies, usages, st.integers(1, 600))
def test_active_block_override_always_blocks(now, policy, usage, minutes) -> None:  # type: ignore[no-untyped-def]
    obs = Observation(observed_at=now, power=Power.ON)
    override = Override(False, now + timedelta(minutes=minutes), now - timedelta(minutes=1))
    assert evaluate(now, obs, policy, usage, (override,)) == Block(BlockReason.OVERRIDE)


@given(instants, usages)
def test_empty_schedule_never_allows_viewing(now, usage) -> None:  # type: ignore[no-untyped-def]
    obs = Observation(observed_at=now, power=Power.ON)
    assert evaluate(now, obs, Policy(), usage) == Block(BlockReason.OUTSIDE_WINDOW)


@given(instants, policies, usages, st.integers(0, 5000))
def test_more_viewing_never_unblocks_the_budget(now, policy, usage, extra) -> None:  # type: ignore[no-untyped-def]
    obs = Observation(observed_at=now, power=Power.ON)
    before = evaluate(now, obs, policy, usage)
    more = Usage(usage.day, usage.watched_seconds + extra, usage.bonus_minutes)
    after = evaluate(now, obs, policy, more)
    if before == Block(BlockReason.BUDGET_EXHAUSTED):
        assert after == before


@given(instants, observations, policies, usages)
def test_warnings_stay_within_thresholds(now, obs, policy, usage) -> None:  # type: ignore[no-untyped-def]
    result = evaluate(now, obs, policy, usage)
    if isinstance(result, Warn):
        assert 0 < result.minutes_left <= max(policy.warn_at_minutes)
        assert result.limit in LimitKind


decisions = st.sampled_from(
    [
        Allow(),
        Warn(5, LimitKind.BUDGET),
        Block(BlockReason.OUTSIDE_WINDOW),
        Block(BlockReason.APP_BLOCKED),
    ]
)
capability_sets = st.sets(st.sampled_from(Capability))
NEEDS = {
    ShowMessage: Capability.ON_SCREEN_MESSAGE,
    GoHome: Capability.GO_HOME,
    PowerOff: Capability.POWER_OFF,
    LaunchApp: Capability.LAUNCH_APP,
    SetInput: Capability.SET_INPUT,
    SetChannel: Capability.SET_CHANNEL,
}


@given(decisions, st.sampled_from(EnforcementLevel), capability_sets)
def test_plans_only_use_available_capabilities(decision: Decision, level, caps) -> None:  # type: ignore[no-untyped-def]
    obs = Observation(observed_at=datetime(2026, 1, 1, tzinfo=UTC), power=Power.ON)
    for action in plan_actions(decision, level, caps, obs, Policy()):
        assert NEEDS[type(action)] in caps


@settings(max_examples=60)
@given(st.lists(st.tuples(decisions, st.integers(1, 30)), min_size=1, max_size=300))
def test_enforcement_safeguards_hold_for_any_sequence(steps) -> None:  # type: ignore[no-untyped-def]
    policy = Policy()
    state, now = EnforcementState(), datetime(2026, 1, 5, 21, tzinfo=ROME)
    obs = Observation(observed_at=now, power=Power.ON)
    power_offs: list[datetime] = []
    redirects = 0
    for decision, gap in steps:
        now += timedelta(seconds=gap)
        result = step(state, now, decision, obs, set(Capability), policy)
        state = result.state
        if state.episode_started is None:
            redirects = 0
        redirects += sum(isinstance(e, Redirected) for e in result.events)
        assert redirects <= 1
        if any(isinstance(a, PowerOff) for a in result.actions):
            power_offs.append(now)
            recent = [t for t in power_offs if now - t < policy.escalation.cap_window]
            assert len(recent) <= policy.escalation.power_off_cap
