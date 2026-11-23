"""Daily viewing budget: remaining time and usage accounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

from tvbalance.domain.content import is_always_allowed
from tvbalance.domain.models import Observation, Policy, Power, Usage

MAX_ACCRUAL_GAP = timedelta(seconds=120)


def base_policy(policy: Policy) -> Policy:
    """The policy without the advanced budgets: what applies when the plan does not include them."""
    return replace(policy, weekday_budget_minutes={}, app_budgets=(), rollover_max_minutes=None)


def daily_budget_minutes(policy: Policy, day: date) -> int | None:
    """The budget of ``day``: its weekday's own one when set, else the general daily budget."""
    return policy.weekday_budget_minutes.get(day.weekday(), policy.daily_budget_minutes)


def rollover_minutes(policy: Policy, yesterday: Usage) -> int:
    """Unused minutes of the previous day that carry over, capped. They never chain."""
    if policy.rollover_max_minutes is None:
        return 0
    budget = daily_budget_minutes(policy, yesterday.day)
    if budget is None:
        return 0
    unused = (budget + yesterday.bonus_minutes) * 60 - yesterday.watched_seconds
    return min(max(0, unused) // 60, policy.rollover_max_minutes)


def remaining_seconds(policy: Policy, usage: Usage, rollover: int = 0) -> int | None:
    """Budget seconds left today, or ``None`` when there is no budget for the day."""
    budget = daily_budget_minutes(policy, usage.day)
    if budget is None:
        return None
    allowed = (budget + rollover + usage.bonus_minutes) * 60
    return max(0, allowed - usage.watched_seconds)


def app_budget_left(
    policy: Policy, app_id: str | None, app_seconds: Mapping[str, int]
) -> int | None:
    """Seconds left of the allowance of the group ``app_id`` belongs to, if it belongs to one."""
    if app_id is None:
        return None
    for group in policy.app_budgets:
        if app_id in group.apps:
            used = sum(app_seconds.get(app, 0) for app in group.apps)
            return max(0, group.minutes * 60 - used)
    return None


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
