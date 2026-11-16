from importlib.metadata import EntryPoint
from unittest.mock import patch

import pytest

from tvbalance.sdk.fake import PLUGIN
from tvbalance.sdk.registry import InvalidAdapterError, load_plugins
from tvbalance.sdk.types import Capability


def test_fake_adapter_is_discovered_through_entry_points() -> None:
    plugins = load_plugins()
    assert "fake" in plugins
    assert plugins["fake"].info.capabilities == frozenset(Capability)


def test_entry_point_name_must_match_declared_id() -> None:
    liar = EntryPoint(name="other", value="tvbalance.sdk.fake:PLUGIN", group="tvbalance.adapters")
    with patch("tvbalance.sdk.registry.entry_points", return_value=[liar]):
        with pytest.raises(InvalidAdapterError, match="does not match"):
            load_plugins()


def test_entry_point_must_be_an_adapter_plugin() -> None:
    bad = EntryPoint(name="x", value="tvbalance.sdk.fake:FakeTV", group="tvbalance.adapters")
    with patch("tvbalance.sdk.registry.entry_points", return_value=[bad]):
        with pytest.raises(InvalidAdapterError, match="not an AdapterPlugin"):
            load_plugins()


def test_plugin_info_is_immutable() -> None:
    with pytest.raises(AttributeError):
        PLUGIN.info.id = "changed"  # type: ignore[misc]
