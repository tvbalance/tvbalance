"""Rule evaluation and action planning. Signatures only; behavior arrives with module M1."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from tvbalance.domain.models import (
    Action,
    Decision,
    Observation,
    Override,
    Policy,
    Usage,
)


def evaluate(
    now: datetime,
    observation: Observation,
    policy: Policy,
    usage: Usage,
    overrides: tuple[Override, ...] = (),
) -> Decision:
    """Decide whether the current observation is allowed. Pure function of its inputs."""
    raise NotImplementedError("module M1")


def plan_actions(
    decision: Decision,
    capabilities: Collection[str],
    observation: Observation,
    policy: Policy,
) -> list[Action]:
    """Choose the escalation steps the TV can actually perform for this decision."""
    raise NotImplementedError("module M1")
