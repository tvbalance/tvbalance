"""Static description of the webOS adapter."""

from tvbalance.sdk.types import AdapterInfo, Capability, Maturity

# WAKE is not declared until the domain has an action to wake a TV (Wake-on-LAN).
INFO = AdapterInfo(
    id="webos",
    brand="LG",
    display_name="LG webOS",
    maturity=Maturity.STABLE,
    capabilities=frozenset(
        {
            Capability.FOREGROUND_APP,
            Capability.LIST_APPS,
            Capability.LAUNCH_APP,
            Capability.GO_HOME,
            Capability.CURRENT_INPUT,
            Capability.SET_INPUT,
            Capability.LIVE_CHANNEL,
            Capability.SET_CHANNEL,
            Capability.PROGRAM_INFO,
            Capability.ON_SCREEN_MESSAGE,
            Capability.POWER_OFF,
            Capability.PUSH_UPDATES,
        }
    ),
)
