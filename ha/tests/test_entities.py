from typing import Any

import aiohttp
import pytest
from custom_components.tvbalance.const import CONF_TOKEN, CONF_URL, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .test_config_flow import ADAPTERS, URL


def make_tv(tv_id: str = "tv1", name: str = "Living room", **overrides: Any) -> dict[str, Any]:
    status = {
        "connected": True,
        "pairing_required": False,
        "power": "on",
        "foreground_app": "YouTube",
        "input_id": None,
        "channel_id": None,
        "program_title": None,
        "decision": {"kind": "allow", "reason": None, "limit": None, "minutes_left": None},
        "watched_seconds": 1500,
        "remaining_seconds": 2700,
        "updated_at": None,
    }
    changes = overrides.pop("status", {})
    tv = {
        "id": tv_id,
        "name": name,
        "adapter_id": "fake",
        "enabled": True,
        "policy_id": 1,
        "needs_pairing": False,
        "status": None if changes is None else {**status, **changes},
    }
    tv.update(overrides)
    return tv


async def setup_engine(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tvs: list[dict[str, Any]]
) -> MockConfigEntry:
    aioclient_mock.get(f"{URL}/api/v1/health", json={"status": "ok"})
    aioclient_mock.get(f"{URL}/api/v1/adapters", json=ADAPTERS)
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=tvs)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=URL, data={CONF_URL: URL, CONF_TOKEN: "secret"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def all_devices(hass: HomeAssistant) -> list[dr.DeviceEntry]:
    """Every TVBalance device (the registry's own mapping is deprecated in newer HA)."""
    registry = dr.async_get(hass)
    return [
        device
        for entry in hass.config_entries.async_entries(DOMAIN)
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
    ]


def state_of(hass: HomeAssistant, domain: str, key: str, device_name: str = "Living room"):
    """The state of the entity with this translation key on the named device."""
    device = next(d for d in all_devices(hass) if d.name == device_name)
    for entity in er.async_entries_for_device(er.async_get(hass), device.id, True):
        if entity.domain == domain and entity.translation_key == key:
            return hass.states.get(entity.entity_id)
    raise AssertionError(f"no {domain} {key} on {device_name}")


async def test_a_tv_becomes_a_device_with_sensors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])

    (device,) = [d for d in all_devices(hass) if d.name == "Living room"]
    assert device.identifiers == {(DOMAIN, "tv1")}
    assert device.manufacturer == "Fake" and device.model == "Fake TV"
    assert state_of(hass, "sensor", "status").state == "watching"
    assert state_of(hass, "sensor", "app").state == "YouTube"
    assert state_of(hass, "sensor", "watched_today").state == "25"
    assert state_of(hass, "sensor", "time_left").state == "45"
    assert state_of(hass, "binary_sensor", "blocked").state == "off"
    assert state_of(hass, "binary_sensor", "connected").state == "on"
    assert state_of(hass, "binary_sensor", "needs_pairing").state == "off"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"status": {"power": "standby"}}, "standby"),
        ({"status": {"power": "off"}}, "off"),
        ({"status": {"connected": False}}, "unreachable"),
        ({"status": None}, "unreachable"),
        ({"needs_pairing": True}, "needs_pairing"),
        ({"status": {"pairing_required": True}}, "needs_pairing"),
        ({"enabled": False}, "not_monitored"),
    ],
)
async def test_status_follows_the_dashboard_rules(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    overrides: dict[str, Any],
    expected: str,
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv(**overrides)])
    assert state_of(hass, "sensor", "status").state == expected


async def test_time_left_is_unknown_without_a_budget(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv(status={"remaining_seconds": None})])
    assert state_of(hass, "sensor", "time_left").state == "unknown"


async def test_a_block_shows_its_reason(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    decision = {"kind": "block", "reason": "outside_schedule", "limit": None, "minutes_left": None}
    await setup_engine(hass, aioclient_mock, [make_tv(status={"decision": decision})])
    blocked = state_of(hass, "binary_sensor", "blocked")
    assert blocked.state == "on"
    assert blocked.attributes["reason"] == "outside_schedule"


async def test_unreachable_engine_after_setup_makes_entities_unavailable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    entry = await setup_engine(hass, aioclient_mock, [make_tv()])
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", exc=aiohttp.ClientConnectionError)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert state_of(hass, "sensor", "status").state == "unavailable"


async def test_the_profile_sensor_names_the_active_profile(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    profile = {
        "policy_id": 2,
        "name": "Holidays",
        "until": "2026-01-01T12:00:00+00:00",
        "source": "calendar",
    }
    await setup_engine(hass, aioclient_mock, [make_tv(status={"active_profile": profile})])
    assert state_of(hass, "sensor", "profile").state == "Holidays"


async def test_the_profile_sensor_is_unknown_without_a_profile(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    assert state_of(hass, "sensor", "profile").state == "unknown"
