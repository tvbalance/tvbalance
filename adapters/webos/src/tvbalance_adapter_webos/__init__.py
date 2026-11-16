"""LG webOS adapter."""

from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import AdapterConfig
from tvbalance_adapter_webos.adapter import WebOsAdapter
from tvbalance_adapter_webos.discovery import discover
from tvbalance_adapter_webos.info import INFO


def _factory(config: AdapterConfig) -> WebOsAdapter:
    return WebOsAdapter(config)


PLUGIN = AdapterPlugin(info=INFO, factory=_factory, discover=discover)
