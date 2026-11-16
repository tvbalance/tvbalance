from datetime import UTC, datetime

import pytest

from tvbalance.domain.models import Allow, Observation, Policy, Power, Usage
from tvbalance.domain.rules import evaluate, plan_actions


def _obs() -> Observation:
    return Observation(observed_at=datetime(2026, 1, 5, 12, tzinfo=UTC), power=Power.ON)


def test_domain_types_are_frozen() -> None:
    with pytest.raises(AttributeError):
        _obs().power = Power.OFF  # type: ignore[misc]


def test_rules_are_declared_but_not_implemented_yet() -> None:
    # Placeholder until module M1 lands real behavior with its own tests.
    now = datetime(2026, 1, 5, 12, tzinfo=UTC)
    with pytest.raises(NotImplementedError):
        evaluate(now, _obs(), Policy(), Usage())
    with pytest.raises(NotImplementedError):
        plan_actions(Allow(), set(), _obs(), Policy())
