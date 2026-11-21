"""TVBalance: thin Home Assistant integration over the TVBalance Engine API."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from tvbalance_client import TVBalanceClient, TVBalanceError

from .const import CONF_TOKEN, CONF_URL
from .coordinator import TVBalanceCoordinator

type TVBalanceConfigEntry = ConfigEntry[TVBalanceCoordinator]

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: TVBalanceConfigEntry) -> bool:
    client = TVBalanceClient(
        entry.data[CONF_URL],
        entry.data.get(CONF_TOKEN),
        session=async_get_clientsession(hass),
    )
    try:
        await client.health()
    except TVBalanceError as ex:
        raise ConfigEntryNotReady(f"TVBalance Engine unavailable: {ex}") from ex
    coordinator = TVBalanceCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_add_listener(coordinator.sync_devices))
    coordinator.start_listening()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TVBalanceConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
