"""The shipped blueprints load through Home Assistant's own blueprint schema."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.util.yaml import load_yaml

BLUEPRINTS = Path(__file__).parents[1] / "blueprints" / "automation" / "tvbalance"


def test_blueprints_exist() -> None:
    assert {p.name for p in BLUEPRINTS.glob("*.yaml")} == {
        "warning_light.yaml",
        "notify_parent.yaml",
        "button_bonus.yaml",
    }


@pytest.mark.parametrize("path", sorted(BLUEPRINTS.glob("*.yaml")), ids=lambda p: p.stem)
def test_blueprint_is_valid(path: Path) -> None:
    blueprint = Blueprint(
        load_yaml(str(path)), expected_domain="automation", schema=BLUEPRINT_SCHEMA
    )
    assert blueprint.metadata["domain"] == "automation"
    assert blueprint.inputs
