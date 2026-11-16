"""Content classification against a policy's always-allowed and blocked sets."""

from __future__ import annotations

from tvbalance.domain.models import BlockReason, Observation, Policy


def is_always_allowed(observation: Observation, policy: Policy) -> bool:
    """True when what is on screen is exempt from time limits and does not use the budget."""
    return (
        (
            observation.foreground_app is not None
            and observation.foreground_app in policy.always_allowed_apps
        )
        or (
            observation.input_id is not None
            and observation.input_id in policy.always_allowed_inputs
        )
        or (
            observation.channel_id is not None
            and observation.channel_id in policy.always_allowed_channels
        )
    )


def blocked_content_reason(observation: Observation, policy: Policy) -> BlockReason | None:
    """Why the current content is blocked regardless of time, or ``None`` when it is acceptable."""
    app = observation.foreground_app
    if app is not None:
        if app in policy.blocked_apps:
            return BlockReason.APP_BLOCKED
        if policy.allow_list_apps is not None and app not in policy.allow_list_apps:
            return BlockReason.APP_BLOCKED
    if observation.input_id is not None and observation.input_id in policy.blocked_inputs:
        return BlockReason.INPUT_BLOCKED
    if observation.channel_id is not None and observation.channel_id in policy.blocked_channels:
        return BlockReason.CHANNEL_BLOCKED
    return None
