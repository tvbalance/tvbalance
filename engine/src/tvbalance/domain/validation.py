"""Static checks of a policy. Issues are reported, never raised: configuration stays savable."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from tvbalance.domain.models import (
    AppTarget,
    ChannelTarget,
    InputTarget,
    Policy,
    TimeWindow,
)


class IssueCode(StrEnum):
    FALLBACK_BLOCKED = "fallback_blocked"
    FALLBACK_NOT_ALWAYS_ALLOWED = "fallback_not_always_allowed"
    CONFLICTING_LISTS = "conflicting_lists"
    INVALID_WARN_THRESHOLD = "invalid_warn_threshold"
    NEGATIVE_BUDGET = "negative_budget"
    OVERLAPPING_WINDOWS = "overlapping_windows"


@dataclass(frozen=True, slots=True)
class PolicyIssue:
    code: IssueCode
    detail: str = ""


def _span(window: TimeWindow) -> tuple[int, int]:
    start = window.start.hour * 60 + window.start.minute
    end = window.end.hour * 60 + window.end.minute
    return start, end if end > start else end + 1440


def _overlap(windows: tuple[TimeWindow, ...]) -> bool:
    spans = sorted(_span(w) for w in windows)
    return any(later[0] < earlier[1] for earlier, later in pairwise(spans))


def _fallback_issues(policy: Policy) -> list[PolicyIssue]:
    target = policy.fallback
    blocked: bool
    exempt: bool
    match target:
        case AppTarget(app_id):
            blocked = app_id in policy.blocked_apps or (
                policy.allow_list_apps is not None and app_id not in policy.allow_list_apps
            )
            exempt = app_id in policy.always_allowed_apps
        case InputTarget(input_id):
            blocked = input_id in policy.blocked_inputs
            exempt = input_id in policy.always_allowed_inputs
        case ChannelTarget(channel_id):
            blocked = channel_id in policy.blocked_channels
            exempt = channel_id in policy.always_allowed_channels
        case _:
            return []
    if blocked and not exempt:
        return [PolicyIssue(IssueCode.FALLBACK_BLOCKED)]
    if not exempt:
        return [PolicyIssue(IssueCode.FALLBACK_NOT_ALWAYS_ALLOWED)]
    return []


def validate_policy(policy: Policy) -> list[PolicyIssue]:
    issues = _fallback_issues(policy)
    for kind, allowed, blocked in (
        ("apps", policy.always_allowed_apps, policy.blocked_apps),
        ("inputs", policy.always_allowed_inputs, policy.blocked_inputs),
        ("channels", policy.always_allowed_channels, policy.blocked_channels),
    ):
        if allowed & blocked:
            issues.append(PolicyIssue(IssueCode.CONFLICTING_LISTS, kind))
    thresholds = policy.warn_at_minutes
    if any(t <= 0 for t in thresholds) or len(set(thresholds)) != len(thresholds):
        issues.append(PolicyIssue(IssueCode.INVALID_WARN_THRESHOLD))
    if policy.daily_budget_minutes is not None and policy.daily_budget_minutes < 0:
        issues.append(PolicyIssue(IssueCode.NEGATIVE_BUDGET))
    day_rules = [*policy.schedule.windows.items(), *policy.schedule.special_days.items()]
    for key, windows in day_rules:
        if _overlap(windows):
            issues.append(PolicyIssue(IssueCode.OVERLAPPING_WINDOWS, str(key)))
    return issues
