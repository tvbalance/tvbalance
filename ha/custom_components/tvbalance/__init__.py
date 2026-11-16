"""TVBalance: thin Home Assistant integration over the TVBalance Engine API."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from tvbalance_client import TVBalanceClient, TVBalanceError

from .const import CONF_TOKEN, CONF_URL

type TVBalanceConfigEntry = ConfigEntry[TVBalanceClient]

PLATFORMS: list[str] = []


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
    entry.runtime_data = client
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TVBalanceConfigEntry) -> bool:
    return True
