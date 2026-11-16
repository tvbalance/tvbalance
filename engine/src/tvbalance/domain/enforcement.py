"""Enforcement state machine: turns a stream of decisions into debounced, bounded actions.

``step`` is a pure function; the supervisor (M3) feeds it each observation and executes the
returned actions. Safeguards: debounce, one warning per threshold, grace between rungs,
one redirect per episode and a cap on power-offs.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from tvbalance.domain.models import (
    Action,
    Allow,
    Block,
    Blocked,
    Decision,
    DomainEvent,
    EnforcementLevel,
    EnforcementPaused,
    EnforcementUnavailable,
    Observation,
    Policy,
    Power,
    PoweredOff,
    PowerOff,
    Redirected,
    TimeWarning,
    Warn,
)
from tvbalance.domain.rules import plan_actions
from tvbalance.sdk.types import Capability


@dataclass(frozen=True, slots=True)
class EnforcementState:
    day: date | None = None
    warned: frozenset[int] = frozenset()
    episode_started: datetime | None = None
    acted_at: datetime | None = None
    last_message_at: datetime | None = None
    redirected: bool = False
    unavailable_reported: bool = False
    power_offs: tuple[datetime, ...] = ()
    paused_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class StepResult:
    state: EnforcementState
    actions: tuple[Action, ...] = ()
    events: tuple[DomainEvent, ...] = field(default=())


def _end_episode(state: EnforcementState) -> EnforcementState:
    return replace(
        state,
        episode_started=None,
        acted_at=None,
        last_message_at=None,
        redirected=False,
        unavailable_reported=False,
    )


def step(
    state: EnforcementState,
    now: datetime,
    decision: Decision,
    observation: Observation,
    capabilities: Collection[Capability],
    policy: Policy,
) -> StepResult:
    """Advance the machine by one observation."""
    if state.day != now.date():
        state = replace(state, day=now.date(), warned=frozenset())
    if state.paused_until is not None and now >= state.paused_until:
        state = replace(state, paused_until=None)

    if observation.power is not Power.ON:
        return StepResult(_end_episode(replace(state, warned=frozenset())))
    if isinstance(decision, Allow):
        return StepResult(_end_episode(replace(state, warned=frozenset())))
    if isinstance(decision, Warn):
        return _warn(state, decision, observation, capabilities, policy)
    return _block(state, now, decision, observation, capabilities, policy)


def _warn(
    state: EnforcementState,
    decision: Warn,
    observation: Observation,
    capabilities: Collection[Capability],
    policy: Policy,
) -> StepResult:
    state = _end_episode(state)
    # A bonus can push the remaining time back above a threshold: re-arm those below it.
    state = replace(state, warned=frozenset(t for t in state.warned if t >= decision.minutes_left))
    crossed = [t for t in policy.warn_at_minutes if t >= decision.minutes_left]
    if not crossed or min(crossed) in state.warned:
        return StepResult(state)
    state = replace(state, warned=state.warned | frozenset(crossed))
    actions = plan_actions(decision, EnforcementLevel.NOTIFY, capabilities, observation, policy)
    return StepResult(state, tuple(actions), (TimeWarning(decision.minutes_left, decision.limit),))


def _block(
    state: EnforcementState,
    now: datetime,
    decision: Block,
    observation: Observation,
    capabilities: Collection[Capability],
    policy: Policy,
) -> StepResult:
    if state.paused_until is not None:
        return StepResult(state)
    esc = policy.escalation
    if state.episode_started is None:
        return StepResult(replace(state, episode_started=now))
    if now - state.episode_started < esc.debounce:
        return StepResult(state)

    def plan(level: EnforcementLevel) -> list[Action]:
        return plan_actions(decision, level, capabilities, observation, policy)

    if state.acted_at is None:
        actions = plan(EnforcementLevel.NOTIFY)
        events: list[DomainEvent] = [Blocked(decision.reason)]
        state = replace(state, acted_at=now, last_message_at=now)
        if not decision.reason.is_time_based:  # blocked content is redirected right away
            redirect = plan(EnforcementLevel.REDIRECT)
            if redirect:
                actions += redirect
                events.append(Redirected(redirect[0]))
                state = replace(state, redirected=True)
        return StepResult(state, tuple(actions), tuple(events))

    if now - state.acted_at < esc.grace:
        return StepResult(state)

    if not state.redirected:
        redirect = plan(EnforcementLevel.REDIRECT)
        if redirect:
            state = replace(state, redirected=True, acted_at=now)
            return StepResult(state, tuple(redirect), (Redirected(redirect[0]),))

    if not plan(EnforcementLevel.POWER_OFF):
        return _unavailable(state, now, decision, plan(EnforcementLevel.NOTIFY), policy)

    recent = tuple(t for t in state.power_offs if now - t < esc.cap_window)
    if len(recent) >= esc.power_off_cap:
        until = now + esc.cap_pause
        paused = replace(_end_episode(state), power_offs=recent, paused_until=until)
        return StepResult(paused, (), (EnforcementPaused(until),))
    ended = replace(_end_episode(state), power_offs=(*recent, now))
    return StepResult(ended, (PowerOff(),), (PoweredOff(),))


def _unavailable(
    state: EnforcementState,
    now: datetime,
    decision: Block,
    message: list[Action],
    policy: Policy,
) -> StepResult:
    """No rung can stop the viewing: report once and keep repeating the on-screen notice."""
    events: tuple[DomainEvent, ...] = ()
    if not state.unavailable_reported:
        events = (EnforcementUnavailable(decision.reason),)
        state = replace(state, unavailable_reported=True)
    actions: tuple[Action, ...] = ()
    last = state.last_message_at
    if message and (last is None or now - last >= policy.escalation.message_repeat):
        actions = tuple(message)
        state = replace(state, last_message_at=now)
    return StepResult(state, actions, events)
