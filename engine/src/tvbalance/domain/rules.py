"""Rule evaluation and action planning. Pure functions of their inputs."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime

from tvbalance.domain.budget import app_budget_left, remaining_seconds
from tvbalance.domain.content import blocked_content_reason, is_always_allowed
from tvbalance.domain.models import (
    Action,
    Allow,
    AppTarget,
    Block,
    BlockReason,
    ChannelTarget,
    Decision,
    EnforcementLevel,
    GoHome,
    InputTarget,
    LaunchApp,
    LimitKind,
    MessageKind,
    Observation,
    Override,
    Policy,
    Power,
    PowerOff,
    SetChannel,
    SetInput,
    ShowMessage,
    Target,
    Usage,
    Warn,
)
from tvbalance.domain.schedule import allowed_span, seconds_until_end
from tvbalance.sdk.types import Capability


def _ceil_minutes(seconds: int) -> int:
    return -(-seconds // 60)


def _active_override(now: datetime, overrides: tuple[Override, ...]) -> Override | None:
    """The most recently created override that is in force at ``now``."""
    active = [o for o in overrides if o.created_at <= now < o.until]
    return max(active, key=lambda o: o.created_at, default=None)


def evaluate(
    now: datetime,
    observation: Observation,
    policy: Policy,
    usage: Usage,
    overrides: tuple[Override, ...] = (),
    rollover: int = 0,
    app_seconds: Mapping[str, int] | None = None,
) -> Decision:
    """Decide whether the current observation is allowed. Pure function of its inputs.

    ``now`` is timezone-aware and expressed in the household's zone. Order of precedence:
    TV not on, block override, always-allowed content, time limits (skipped under an allow
    override), blocked content, then warnings for the nearest upcoming limit.
    """
    if observation.power is not Power.ON:
        return Allow()

    override = _active_override(now, overrides)
    if override is not None and not override.allow:
        return Block(BlockReason.OVERRIDE)
    if is_always_allowed(observation, policy):
        return Allow()

    # (seconds left, kind) of every limit that will end viewing, nearest first after min().
    upcoming: list[tuple[int, LimitKind]] = []
    if override is not None:
        upcoming.append((int((override.until - now).total_seconds()), LimitKind.OVERRIDE))
    else:
        span = allowed_span(policy.schedule, now)
        if span is None:
            return Block(BlockReason.OUTSIDE_WINDOW)
        budget_left = remaining_seconds(policy, usage, rollover)
        if budget_left is not None:
            if budget_left <= 0:
                return Block(BlockReason.BUDGET_EXHAUSTED)
            upcoming.append((budget_left, LimitKind.BUDGET))
        upcoming.append((seconds_until_end(span, now), LimitKind.WINDOW))
        group_left = app_budget_left(policy, observation.foreground_app, app_seconds or {})
        if group_left is not None:
            if group_left <= 0:
                return Block(BlockReason.APP_BUDGET_EXHAUSTED)
            upcoming.append((group_left, LimitKind.APP_BUDGET))

    reason = blocked_content_reason(observation, policy)
    if reason is not None:
        return Block(reason)

    if policy.warn_at_minutes:
        seconds, kind = min(upcoming, key=lambda item: item[0])
        minutes = _ceil_minutes(seconds)
        if 0 < minutes <= max(policy.warn_at_minutes):
            return Warn(minutes, kind)
    return Allow()


def _fallback_action(
    target: Target | None, capabilities: Collection[Capability], policy: Policy, *, exempt: bool
) -> Action | None:
    """The action that moves the TV to ``target``, or ``None`` when unusable.

    ``exempt`` requires the target to be always-allowed (needed for time limits, where only
    exempt content is viewable); otherwise it only has to be free of content blocks.
    """
    match target:
        case AppTarget(app_id) if Capability.LAUNCH_APP in capabilities:
            listed = policy.allow_list_apps is None or app_id in policy.allow_list_apps
            ok = app_id in policy.always_allowed_apps or (
                not exempt and app_id not in policy.blocked_apps and listed
            )
            return LaunchApp(app_id) if ok else None
        case InputTarget(input_id) if Capability.SET_INPUT in capabilities:
            ok = input_id in policy.always_allowed_inputs or (
                not exempt and input_id not in policy.blocked_inputs
            )
            return SetInput(input_id) if ok else None
        case ChannelTarget(channel_id) if Capability.SET_CHANNEL in capabilities:
            ok = channel_id in policy.always_allowed_channels or (
                not exempt and channel_id not in policy.blocked_channels
            )
            return SetChannel(channel_id) if ok else None
    return None


def plan_actions(
    decision: Decision,
    level: EnforcementLevel,
    capabilities: Collection[Capability],
    observation: Observation,
    policy: Policy,
) -> list[Action]:
    """Translate one rung of the escalation ladder into actions the TV can perform.

    An empty list means the rung is unavailable; the caller then moves to the next one.
    """
    if isinstance(decision, Allow):
        return []
    can_message = Capability.ON_SCREEN_MESSAGE in capabilities
    if isinstance(decision, Warn):
        if level is EnforcementLevel.NOTIFY and can_message:
            return [ShowMessage(MessageKind.TIME_WARNING, decision.minutes_left)]
        return []

    time_limit = decision.reason.is_time_based
    if level is EnforcementLevel.NOTIFY:
        kind = MessageKind.TIME_UP if time_limit else MessageKind.CONTENT_BLOCKED
        return [ShowMessage(kind)] if can_message else []
    if level is EnforcementLevel.POWER_OFF:
        return [PowerOff()] if Capability.POWER_OFF in capabilities else []

    action = _fallback_action(policy.fallback, capabilities, policy, exempt=time_limit)
    if action is not None:
        return [action]
    if not time_limit and Capability.GO_HOME in capabilities:
        return [GoHome()]
    return []
