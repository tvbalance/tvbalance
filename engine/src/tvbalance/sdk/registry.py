"""Adapter discovery through Python entry points."""

from __future__ import annotations

from importlib.metadata import entry_points

from tvbalance.sdk.plugin import AdapterPlugin

ENTRY_POINT_GROUP = "tvbalance.adapters"


class InvalidAdapterError(Exception):
    """An installed adapter package does not honor the SDK contract."""


def load_plugins() -> dict[str, AdapterPlugin]:
    """Load every installed adapter, keyed by adapter id.

    The entry point name must equal the plugin's declared id so that a package cannot
    register under a misleading name.
    """
    plugins: dict[str, AdapterPlugin] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        plugin = ep.load()
        if not isinstance(plugin, AdapterPlugin):
            raise InvalidAdapterError(f"{ep.name}: entry point is not an AdapterPlugin")
        if plugin.info.id != ep.name:
            raise InvalidAdapterError(
                f"{ep.name}: declared id {plugin.info.id!r} does not match the entry point name"
            )
        plugins[plugin.info.id] = plugin
    return plugins
