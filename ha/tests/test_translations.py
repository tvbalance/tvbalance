import json
from pathlib import Path
from typing import Any

import pytest

FOLDER = Path(__file__).parents[1] / "custom_components" / "tvbalance" / "translations"
LANGUAGES = ["it", "de", "fr", "es"]


def _load(language: str) -> dict[str, Any]:
    return json.loads((FOLDER / f"{language}.json").read_text(encoding="utf-8"))


def _keys(node: Any, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return {prefix}
    return {key for name, child in node.items() for key in _keys(child, f"{prefix}.{name}")}


def _placeholders(node: Any, prefix: str = "") -> dict[str, set[str]]:
    if isinstance(node, dict):
        found: dict[str, set[str]] = {}
        for name, child in node.items():
            found |= _placeholders(child, f"{prefix}.{name}")
        return found
    import re

    return {prefix: set(re.findall(r"\{(\w+)\}", node))}


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_the_same_keys_as_english(language: str) -> None:
    english = _load("en")
    assert _keys(_load(language)) == _keys(english)


@pytest.mark.parametrize("language", LANGUAGES)
def test_placeholders_match_english(language: str) -> None:
    assert _placeholders(_load(language)) == _placeholders(_load("en"))
