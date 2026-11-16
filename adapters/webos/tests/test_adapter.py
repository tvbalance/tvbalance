import asyncio
from collections.abc import AsyncIterator

import pytest

from tvbalance.app.session import SessionTimeouts, TVSession
from tvbalance.domain.models import (
    GoHome,
    LaunchApp,
    MessageKind,
    Power,
    PowerOff,
    SetChannel,
    SetInput,
    ShowMessage,
)
from tvbalance.sdk.errors import TVError, TVPairingError, TVTimeoutError
from tvbalance.sdk.types import AdapterConfig, AppInfo, ChannelInfo, InputInfo
from tvbalance_adapter_webos.adapter import WebOsAdapter
from tvbalance_adapter_webos.testing import SimulatedWebOsTV


@pytest.fixture
async def tv() -> AsyncIterator[SimulatedWebOsTV]:
    sim = SimulatedWebOsTV()
    await sim.start()
    yield sim
    await sim.stop()


@pytest.fixture
async def adapter(tv: SimulatedWebOsTV) -> AsyncIterator[WebOsAdapter]:
    adapter = WebOsAdapter(AdapterConfig(tv.host, {"client_key": tv.client_key}))
    await adapter.connect()
    yield adapter
    await adapter.close()


async def test_livetv_is_observed_as_a_channel_with_its_program(
    adapter: WebOsAdapter,
) -> None:
    obs = await adapter.observe()
    assert obs.power is Power.ON
    assert obs.foreground_app is None
    assert obs.channel_id == "ch-news"
    assert obs.program_title == "Evening News"
    assert obs.observed_at.tzinfo is not None


async def test_program_title_is_best_effort(tv: SimulatedWebOsTV, adapter: WebOsAdapter) -> None:
    tv.program_name = None
    obs = await adapter.observe()
    assert obs.channel_id == "ch-news"
    assert obs.program_title is None


async def test_hdmi_is_observed_as_an_input(tv: SimulatedWebOsTV, adapter: WebOsAdapter) -> None:
    await tv.set_app("com.webos.app.hdmi2")
    await asyncio.sleep(0.1)
    obs = await adapter.observe()
    assert (obs.foreground_app, obs.input_id, obs.channel_id) == (None, "HDMI_2", None)


async def test_regular_app_is_observed_as_foreground(
    tv: SimulatedWebOsTV, adapter: WebOsAdapter
) -> None:
    await tv.set_app("video")
    await asyncio.sleep(0.1)
    obs = await adapter.observe()
    assert (obs.foreground_app, obs.input_id, obs.channel_id) == ("video", None, None)


async def test_standby_has_no_content(tv: SimulatedWebOsTV, adapter: WebOsAdapter) -> None:
    await tv.set_power(Power.STANDBY)
    obs = await adapter.observe()
    assert obs.power is Power.STANDBY
    assert (obs.foreground_app, obs.input_id, obs.channel_id) == (None, None, None)


async def test_inventory(adapter: WebOsAdapter) -> None:
    assert AppInfo("kids", "Kids Corner", None) in await adapter.list_apps()
    assert await adapter.list_inputs() == [
        InputInfo("HDMI_1", "HDMI 1"),
        InputInfo("HDMI_2", "HDMI 2"),
    ]
    assert ChannelInfo("ch-news", "News 24", "7") in await adapter.list_channels()


async def test_inventory_ignores_junk_rows(tv: SimulatedWebOsTV, adapter: WebOsAdapter) -> None:
    tv.junk_rows = True
    assert len(await adapter.list_inputs()) == 2
    assert len(await adapter.list_channels()) == 2
    assert len(await adapter.list_apps()) == 2


async def test_actions_send_the_expected_commands(
    tv: SimulatedWebOsTV, adapter: WebOsAdapter
) -> None:
    await adapter.execute(ShowMessage(MessageKind.TIME_UP))
    await adapter.execute(ShowMessage(MessageKind.TIME_UP, text="Custom text"))
    await adapter.execute(LaunchApp("kids"))
    await adapter.execute(SetInput("HDMI_1"))
    await adapter.execute(SetChannel("ch-one"))
    await adapter.execute(PowerOff())
    await adapter.execute(GoHome())
    await asyncio.sleep(0.1)
    toasts = [p["message"] for u, p in tv.commands if u == "system.notifications/createToast"]
    assert toasts[0] != "Custom text"
    assert toasts[1] == "Custom text"
    rest = [(u, p) for u, p in tv.commands if u != "system.notifications/createToast"]
    assert rest == [
        ("system.launcher/launch", {"id": "kids"}),
        ("tv/switchInput", {"inputId": "HDMI_1"}),
        ("tv/openChannel", {"channelId": "ch-one"}),
        ("system/turnOff", {}),
    ]
    assert tv.buttons == ["HOME"]


async def test_observe_before_connect_raises(tv: SimulatedWebOsTV) -> None:
    adapter = WebOsAdapter(AdapterConfig(tv.host, {"client_key": tv.client_key}))
    with pytest.raises(TVError):
        await adapter.observe()


async def test_connect_without_a_key_asks_for_pairing(tv: SimulatedWebOsTV) -> None:
    adapter = WebOsAdapter(AdapterConfig(tv.host, {}))
    with pytest.raises(TVPairingError):
        await adapter.connect()
    assert tv.registered_keys == []  # no prompt was triggered on the TV


async def test_connect_with_a_stale_key_asks_for_pairing(tv: SimulatedWebOsTV) -> None:
    tv.pairing_prompt = "reject"
    adapter = WebOsAdapter(AdapterConfig(tv.host, {"client_key": "revoked"}))
    with pytest.raises(TVPairingError):
        await adapter.connect()


async def test_unreachable_tv_is_a_tv_error() -> None:
    adapter = WebOsAdapter(AdapterConfig("203.0.113.1.invalid", {"client_key": "k"}))
    with pytest.raises(TVError):
        await adapter.connect()


async def test_close_is_idempotent_and_reconnect_works(tv: SimulatedWebOsTV) -> None:
    adapter = WebOsAdapter(AdapterConfig(tv.host, {"client_key": tv.client_key}))
    await adapter.connect()
    await adapter.close()
    await adapter.close()
    await adapter.connect()
    assert (await adapter.observe()).power is Power.ON
    await adapter.close()


async def test_a_dropped_connection_is_a_tv_error(
    tv: SimulatedWebOsTV, adapter: WebOsAdapter
) -> None:
    await tv.drop()
    await asyncio.sleep(0.1)
    with pytest.raises(TVError):
        await adapter.observe()


async def test_mute_peer_times_out_under_a_session_instead_of_looking_online(
    tv: SimulatedWebOsTV, adapter: WebOsAdapter
) -> None:
    tv.mute = True
    session = TVSession(adapter, SessionTimeouts(observe=0.3))
    with pytest.raises(TVTimeoutError):
        await session.observe()


async def test_push_notifies_on_state_changes_until_unsubscribed(
    tv: SimulatedWebOsTV, adapter: WebOsAdapter
) -> None:
    calls: list[int] = []
    unsubscribe = adapter.on_change(lambda: calls.append(1))
    await tv.set_app("video")
    await asyncio.sleep(0.1)
    assert calls
    unsubscribe()
    seen = len(calls)
    await tv.set_app("kids")
    await asyncio.sleep(0.1)
    assert len(calls) == seen
