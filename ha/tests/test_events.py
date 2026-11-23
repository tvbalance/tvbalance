import asyncio
from datetime import timedelta
from typing import Any

import pytest
from custom_components.tvbalance import coordinator as coordinator_module
from custom_components.tvbalance.const import DOMAIN, EVENT_NAME
from homeassistant.core import Event, HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from tvbalance_client import AuthenticationError, TVBalanceConnectionError

from .conftest import EventStream
from .test_config_flow import URL
from .test_entities import all_devices, make_tv, setup_engine, state_of


async def poll(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()


def devices(hass: HomeAssistant) -> set[str]:
    return {d.name for d in all_devices(hass) if d.name}


async def test_a_status_message_updates_the_states_at_once(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    assert state_of(hass, "sensor", "app").state == "YouTube"

    status: dict[str, Any] = make_tv(status={"foreground_app": "Netflix", "power": "standby"})[
        "status"
    ]
    stream.push_status("tv1", status)
    await hass.async_block_till_done()

    assert state_of(hass, "sensor", "app").state == "Netflix"
    assert state_of(hass, "sensor", "status").state == "standby"


async def test_a_status_for_an_unknown_tv_triggers_a_refresh(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[make_tv(), make_tv("tv2", "Bedroom")])

    stream.push_status("tv2", make_tv("tv2")["status"])
    await hass.async_block_till_done()

    assert "Bedroom" in devices(hass)


async def test_an_engine_event_reaches_the_bus_and_the_event_entity(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    fired: list[Event] = async_capture_events(hass, EVENT_NAME)

    stream.push("time_warning", minutes_left=5)
    await hass.async_block_till_done()

    (device,) = [d for d in all_devices(hass) if d.name == "Living room"]
    (event,) = fired
    assert event.data == {
        "device_id": device.id,
        "tv_id": "tv1",
        "type": "time_warning",
        "payload": {"minutes_left": 5},
    }
    activity = state_of(hass, "event", "activity")
    assert activity.attributes["event_type"] == "time_warning"
    assert activity.attributes["minutes_left"] == 5


async def test_the_weekly_report_is_an_event_of_the_entity(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])

    stream.push("weekly_report", total_seconds=7200, blocks=3)
    await hass.async_block_till_done()

    activity = state_of(hass, "event", "activity")
    assert activity.attributes["event_type"] == "weekly_report"
    assert activity.attributes["blocks"] == 3


async def test_events_the_entity_does_not_know_still_reach_the_bus(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    fired = async_capture_events(hass, EVENT_NAME)

    stream.push("tv_added")
    stream.push("something_global", tv_id=None)
    await hass.async_block_till_done()

    assert [e.data["type"] for e in fired] == ["tv_added", "something_global"]
    assert fired[1].data["device_id"] is None
    assert state_of(hass, "event", "activity").attributes["event_type"] is None


async def test_a_dropped_stream_is_reopened(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    stream: EventStream,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(coordinator_module, "RECONNECT_MIN", 0)
    await setup_engine(hass, aioclient_mock, [make_tv()])
    assert stream.connections == 1

    async def reconnected(count: int) -> None:
        async with asyncio.timeout(5):
            # background tasks are not awaited by the hass
            while stream.connections < count:  # noqa: ASYNC110
                await asyncio.sleep(0)

    stream.fail(TVBalanceConnectionError("down"))
    await reconnected(2)
    stream.drop()
    await reconnected(3)

    fired = async_capture_events(hass, EVENT_NAME)
    stream.push("blocked")
    await hass.async_block_till_done()
    assert len(fired) == 1


async def test_a_refused_stream_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, stream: EventStream
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])

    stream.fail(AuthenticationError("no", status=401))
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_a_new_tv_gets_entities_and_a_removed_tv_loses_its_device(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    assert devices(hass) == {"Living room"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[make_tv(), make_tv("tv2", "Bedroom")])
    await poll(hass)
    assert devices(hass) == {"Living room", "Bedroom"}
    assert state_of(hass, "sensor", "status", "Bedroom").state == "watching"

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[make_tv("tv2", "Bedroom")])
    await poll(hass)
    assert devices(hass) == {"Bedroom"}


async def test_a_renamed_tv_renames_its_device(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[make_tv(name="Den")])
    await poll(hass)

    assert devices(hass) == {"Den"}
