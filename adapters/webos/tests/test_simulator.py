"""The simulator must be faithful enough for the real client library to connect to it."""

import asyncio
from collections.abc import AsyncIterator

import pytest
from aiowebostv import WebOsClient, WebOsTvPairError

from tvbalance.domain.models import Power
from tvbalance_adapter_webos._client import RedirectingSession, make_client
from tvbalance_adapter_webos.testing import SimulatedWebOsTV


@pytest.fixture
async def tv() -> AsyncIterator[SimulatedWebOsTV]:
    sim = SimulatedWebOsTV()
    await sim.start()
    yield sim
    await sim.stop()


async def _client(tv: SimulatedWebOsTV, key: str | None) -> tuple[WebOsClient, RedirectingSession]:
    client, session = make_client(tv.host, key)
    assert session is not None
    return client, session


async def test_library_connects_with_a_known_key_and_sees_state(tv: SimulatedWebOsTV) -> None:
    client, session = await _client(tv, tv.client_key)
    assert await client.connect()
    assert client.tv_state.current_app_id == "com.webos.app.livetv"
    assert "com.webos.app.hdmi1" in client.tv_state.inputs
    await client.disconnect()
    await session.close()


async def test_pairing_prompt_accepted_returns_the_key(tv: SimulatedWebOsTV) -> None:
    client, session = await _client(tv, None)
    assert await client.connect()
    assert client.client_key == tv.client_key
    await client.disconnect()
    await session.close()


async def test_pairing_prompt_rejected_raises(tv: SimulatedWebOsTV) -> None:
    tv.pairing_prompt = "reject"
    client, session = await _client(tv, None)
    with pytest.raises(WebOsTvPairError):
        await client.connect()
    await session.close()


async def test_commands_and_buttons_are_recorded(tv: SimulatedWebOsTV) -> None:
    client, session = await _client(tv, tv.client_key)
    await client.connect()
    await client.send_message("hi")
    await client.set_channel("ch-one")
    await client.button("HOME")
    await asyncio.sleep(0.05)
    await client.disconnect()
    await session.close()
    assert ("tv/openChannel", {"channelId": "ch-one"}) in tv.commands
    assert any(uri == "system.notifications/createToast" for uri, _ in tv.commands)
    assert tv.buttons == ["HOME"]


async def test_power_push_reaches_the_client(tv: SimulatedWebOsTV) -> None:
    client, session = await _client(tv, tv.client_key)
    await client.connect()
    await tv.set_power(Power.STANDBY)
    for _ in range(50):
        if not client.tv_state.is_on:
            break
        await asyncio.sleep(0.02)
    assert not client.tv_state.is_on
    await client.disconnect()
    await session.close()
