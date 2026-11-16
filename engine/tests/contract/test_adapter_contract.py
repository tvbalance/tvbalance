"""Contract every adapter must honor. Parametrized over all installed adapters.

Adapters listed in IMPLEMENTED must pass the behavioral tests. The others are declared stubs:
their behavioral tests are xfail(strict), so finishing an adapter forces it into IMPLEMENTED.
"""

import pytest

from tvbalance.domain.models import Observation
from tvbalance.sdk.errors import TVError
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.registry import load_plugins
from tvbalance.sdk.types import AdapterConfig, AppInfo, Capability, Maturity, PairingState

IMPLEMENTED = {"fake"}

PLUGINS = load_plugins()
CONFIG = AdapterConfig(host="127.0.0.1", credentials={})


def _behavioral(plugin_id: str) -> pytest.ParameterSet:
    marks = []
    if plugin_id not in IMPLEMENTED:
        marks.append(pytest.mark.xfail(strict=True, raises=NotImplementedError, reason="stub"))
    return pytest.param(plugin_id, id=plugin_id, marks=marks)


ALL = sorted(PLUGINS)
BEHAVIORAL = [_behavioral(p) for p in ALL]


def test_expected_brands_are_registered() -> None:
    assert {"webos", "roku", "androidtv", "samsung", "fake"} <= set(PLUGINS)


@pytest.mark.parametrize("plugin_id", ALL)
def test_static_metadata(plugin_id: str) -> None:
    info = PLUGINS[plugin_id].info
    assert info.id == plugin_id
    assert info.brand and info.display_name
    assert isinstance(info.maturity, Maturity)
    assert info.capabilities <= frozenset(Capability)
    assert info.capabilities, "an adapter must declare at least one capability"


@pytest.mark.parametrize("plugin_id", ALL)
def test_only_the_reference_adapter_claims_stable_without_implementation(plugin_id: str) -> None:
    info = PLUGINS[plugin_id].info
    if info.maturity is Maturity.STABLE:
        assert plugin_id in {"webos"}, "stable is reserved for adapters verified on hardware"


def _plugin(plugin_id: str) -> AdapterPlugin:
    return PLUGINS[plugin_id]


@pytest.mark.parametrize("plugin_id", BEHAVIORAL)
async def test_connect_observe_close(plugin_id: str) -> None:
    adapter = _plugin(plugin_id).factory(CONFIG)
    await adapter.connect()
    obs = await adapter.observe()
    assert isinstance(obs, Observation)
    assert obs.observed_at.tzinfo is not None, "observations must carry timezone-aware times"
    await adapter.close()
    await adapter.close()  # closing twice must be safe


@pytest.mark.parametrize("plugin_id", BEHAVIORAL)
async def test_inventory_matches_declared_capabilities(plugin_id: str) -> None:
    plugin = _plugin(plugin_id)
    adapter = plugin.factory(CONFIG)
    await adapter.connect()
    if Capability.LIST_APPS in plugin.info.capabilities:
        apps = await adapter.list_apps()
        assert all(isinstance(a, AppInfo) and a.app_id for a in apps)
    await adapter.close()


@pytest.mark.parametrize("plugin_id", BEHAVIORAL)
async def test_pairing_flow_reaches_a_terminal_state(plugin_id: str) -> None:
    flow = _plugin(plugin_id).factory(CONFIG).pairing()
    state = await flow.start()
    for _ in range(3):
        if state in {PairingState.COMPLETED, PairingState.FAILED}:
            break
        state = await flow.poll()
    assert state in {PairingState.COMPLETED, PairingState.FAILED}
    if state is PairingState.COMPLETED:
        assert flow.credentials()


@pytest.mark.parametrize("plugin_id", BEHAVIORAL)
async def test_observe_without_connection_raises_typed_error(plugin_id: str) -> None:
    adapter = _plugin(plugin_id).factory(CONFIG)
    with pytest.raises(TVError):
        await adapter.observe()
