"""Samsung Tizen adapter: declared stub.

Capabilities are EXPECTED values and must be confirmed by a feasibility spike.
"""

from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.stub import StubAdapter
from tvbalance.sdk.types import AdapterConfig, AdapterInfo, Capability, Maturity

INFO = AdapterInfo(
    id="samsung",
    brand="Samsung",
    display_name="Samsung Tizen",
    maturity=Maturity.BETA,
    capabilities=frozenset(
        {
            Capability.LIST_APPS,
            Capability.LAUNCH_APP,
            Capability.GO_HOME,
            Capability.POWER_OFF,
            Capability.WAKE,
        }
    ),
)


def _factory(config: AdapterConfig) -> StubAdapter:
    return StubAdapter(config)


PLUGIN = AdapterPlugin(info=INFO, factory=_factory)
