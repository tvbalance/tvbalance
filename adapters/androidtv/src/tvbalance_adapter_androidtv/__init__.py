"""Google TV / Android TV adapter: declared stub.

Capabilities are EXPECTED values and must be confirmed by a feasibility spike.
"""

from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.stub import StubAdapter
from tvbalance.sdk.types import AdapterConfig, AdapterInfo, Capability, Maturity

INFO = AdapterInfo(
    id="androidtv",
    brand="Google",
    display_name="Google TV / Android TV",
    maturity=Maturity.BETA,
    capabilities=frozenset(
        {
            Capability.FOREGROUND_APP,
            Capability.LAUNCH_APP,
            Capability.GO_HOME,
            Capability.POWER_OFF,
            Capability.WAKE,
            Capability.PUSH_UPDATES,
        }
    ),
)


def _factory(config: AdapterConfig) -> StubAdapter:
    return StubAdapter(config)


PLUGIN = AdapterPlugin(info=INFO, factory=_factory)
