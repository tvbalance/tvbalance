"""The product ships as one version in four places, and the client pins to its own."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_release", ROOT / "scripts/check_release.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


check_release = _load()


def test_the_repository_versions_agree() -> None:
    assert check_release.problems(ROOT) == []


def test_the_integration_pins_the_client_it_ships_with() -> None:
    manifest = json.loads(
        (ROOT / "ha/custom_components/tvbalance/manifest.json").read_text("utf-8")
    )
    versions = check_release.versions(ROOT)
    assert manifest["requirements"] == [f"tvbalance-client=={versions.client}"]


def test_a_product_tag_must_match_the_product_version() -> None:
    version = check_release.versions(ROOT).product
    assert check_release.tag_problems(ROOT, f"v{version}") == []
    assert check_release.tag_problems(ROOT, "v9.9.9") != []


def test_a_client_tag_must_match_the_client_version() -> None:
    version = check_release.versions(ROOT).client
    assert check_release.tag_problems(ROOT, f"client-v{version}") == []
    assert check_release.tag_problems(ROOT, "client-v9.9.9") != []


@pytest.mark.parametrize("tag", ["1.0.0", "release", "vx", ""])
def test_an_unknown_tag_shape_is_refused(tag: str) -> None:
    assert check_release.tag_problems(ROOT, tag) != []
