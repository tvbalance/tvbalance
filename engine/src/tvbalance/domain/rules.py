"""Rule evaluation and action planning. Pure functions of their inputs."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from tvbalance.domain.budget import remaining_seconds
from tvbalance.domain.content import blocked_content_reason, is_always_allowed
from tvbalance.domain.models import (
    Action,
    Allow,
    Block,
    BlockReason,
    Decision,
    LimitKind,
    Observation,
    Override,
    Policy,
    Power,
    Usage,
    Warn,
)
from tvbalance.domain.schedule import allowed_span, seconds_until_end


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
        budget_left = remaining_seconds(policy, usage)
        if budget_left is not None:
            if budget_left <= 0:
                return Block(BlockReason.BUDGET_EXHAUSTED)
            upcoming.append((budget_left, LimitKind.BUDGET))
        upcoming.append((seconds_until_end(span, now), LimitKind.WINDOW))

    reason = blocked_content_reason(observation, policy)
    if reason is not None:
        return Block(reason)

    if policy.warn_at_minutes:
        seconds, kind = min(upcoming, key=lambda item: item[0])
        minutes = _ceil_minutes(seconds)
        if 0 < minutes <= max(policy.warn_at_minutes):
            return Warn(minutes, kind)
    return Allow()


def plan_actions(
    decision: Decision,
    capabilities: Collection[str],
    observation: Observation,
    policy: Policy,
) -> list[Action]:
    """Choose the escalation steps the TV can actually perform for this decision."""
    raise NotImplementedError("module M1")
