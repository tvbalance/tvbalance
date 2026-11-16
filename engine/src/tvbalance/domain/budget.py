"""Daily viewing budget: remaining time and usage accounting."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from tvbalance.domain.content import is_always_allowed
from tvbalance.domain.models import Observation, Policy, Power, Usage

MAX_ACCRUAL_GAP = timedelta(seconds=120)


def remaining_seconds(policy: Policy, usage: Usage) -> int | None:
    """Budget seconds left today, or ``None`` when the policy has no daily budget."""
    if policy.daily_budget_minutes is None:
        return None
    allowed = (policy.daily_budget_minutes + usage.bonus_minutes) * 60
    return max(0, allowed - usage.watched_seconds)


def accrue(
    usage: Usage,
    last_tick: datetime,
    now: datetime,
    observation: Observation,
    policy: Policy,
    max_gap: timedelta = MAX_ACCRUAL_GAP,
) -> Usage:
    """Add the time since ``last_tick`` to ``usage`` when the TV was on with budgeted content.

    A new local day starts from zero (bonus included). Gaps longer than ``max_gap`` are capped so
    a stalled supervisor or a clock jump cannot bill time that was never observed.
    """
    for moment in (last_tick, now):
        if moment.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
    today = now.date()
    if usage.day != today:
        usage = Usage(day=today)
    midnight = datetime.combine(today, time.min, tzinfo=now.tzinfo).astimezone(UTC)
    start = max(last_tick.astimezone(UTC), midnight)
    elapsed = min(now.astimezone(UTC) - start, max_gap)
    if elapsed <= timedelta(0):
        return usage
    if observation.power is not Power.ON or is_always_allowed(observation, policy):
        return usage
    return Usage(
        day=usage.day,
        watched_seconds=usage.watched_seconds + round(elapsed.total_seconds()),
        bonus_minutes=usage.bonus_minutes,
    )
