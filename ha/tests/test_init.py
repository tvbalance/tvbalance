import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.tvbalance.const import CONF_TOKEN, CONF_URL, DOMAIN

from .test_config_flow import INFO, URL


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, unique_id=URL, data={CONF_URL: URL, CONF_TOKEN: "secret"}
    )


async def test_setup_and_unload(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/v1/health", json={"status": "ok"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_engine_is_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/health", exc=aiohttp.ClientConnectionError)
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_diagnostics_redact_the_token(
    hass: HomeAssistant, hass_client, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/health", json={"status": "ok"})
    aioclient_mock.get(f"{URL}/api/v1/info", json=INFO)
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    diag = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diag["entry"][CONF_TOKEN] == "**REDACTED**"
    assert diag["engine"]["adapters"][0]["id"] == "fake"
