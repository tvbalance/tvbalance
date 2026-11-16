"""Commands that change a real LG TV: run only in a supervised session (``hardware_actions``).

    TVBALANCE_WEBOS_HOST=... TVBALANCE_WEBOS_KEY=... uv run pytest -m hardware_actions -s

Each step waits for the person in front of the TV, who confirms what they saw.
"""

import asyncio
import os
from collections.abc import AsyncIterator

import pytest

from tvbalance.domain.models import GoHome, MessageKind, PowerOff, SetChannel, ShowMessage
from tvbalance.sdk.types import AdapterConfig
from tvbalance_adapter_webos.adapter import WebOsAdapter

pytestmark = pytest.mark.hardware_actions


@pytest.fixture
async def adapter() -> AsyncIterator[WebOsAdapter]:
    host, key = os.environ.get("TVBALANCE_WEBOS_HOST"), os.environ.get("TVBALANCE_WEBOS_KEY")
    if not host or not key:
        pytest.skip("TVBALANCE_WEBOS_HOST and TVBALANCE_WEBOS_KEY are not set")
    adapter = WebOsAdapter(AdapterConfig(host, {"client_key": key}))
    await adapter.connect()
    yield adapter
    await adapter.close()


async def test_message_appears(adapter: WebOsAdapter) -> None:
    await adapter.execute(ShowMessage(MessageKind.TIME_WARNING, 5))
    await asyncio.sleep(3)


async def test_home_button(adapter: WebOsAdapter) -> None:
    await adapter.execute(GoHome())
    await asyncio.sleep(3)


async def test_channel_change_by_id(adapter: WebOsAdapter) -> None:
    channels = await adapter.list_channels()
    assert len(channels) >= 2
    current = (await adapter.observe()).channel_id
    target = next(c for c in channels if c.channel_id != current)
    await adapter.execute(SetChannel(target.channel_id))
    await asyncio.sleep(5)
    assert (await adapter.observe()).channel_id == target.channel_id


async def test_power_off(adapter: WebOsAdapter) -> None:
    await adapter.execute(PowerOff())
