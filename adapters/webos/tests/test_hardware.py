"""Read-only checks against a real LG TV. Excluded by default (marker ``hardware``).

    TVBALANCE_WEBOS_HOST=<tv address> TVBALANCE_WEBOS_KEY=<client key> uv run pytest -m hardware

The key comes from pairing once (see docs/user-guide/tv-lg-webos.md). Nothing here changes the TV.
"""

import os
from collections.abc import AsyncIterator

import pytest

from tvbalance.domain.models import Observation, Power
from tvbalance.sdk.types import AdapterConfig
from tvbalance_adapter_webos.adapter import WebOsAdapter

pytestmark = pytest.mark.hardware


@pytest.fixture
async def adapter() -> AsyncIterator[WebOsAdapter]:
    host, key = os.environ.get("TVBALANCE_WEBOS_HOST"), os.environ.get("TVBALANCE_WEBOS_KEY")
    if not host or not key:
        pytest.skip("TVBALANCE_WEBOS_HOST and TVBALANCE_WEBOS_KEY are not set")
    adapter = WebOsAdapter(AdapterConfig(host, {"client_key": key}))
    await adapter.connect()
    yield adapter
    await adapter.close()


async def test_observe_reports_a_consistent_state(adapter: WebOsAdapter) -> None:
    obs = await adapter.observe()
    assert isinstance(obs, Observation)
    assert obs.power in set(Power)
    if obs.power is not Power.ON:
        assert (obs.foreground_app, obs.input_id, obs.channel_id) == (None, None, None)
    print(obs)


async def test_inventories_are_not_empty(adapter: WebOsAdapter) -> None:
    assert await adapter.list_apps()
    assert await adapter.list_inputs()
    assert await adapter.list_channels()
