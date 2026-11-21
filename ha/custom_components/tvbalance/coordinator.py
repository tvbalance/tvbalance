"""Keeps the state of every TV, polled from the Engine."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from tvbalance_client import (
    AdapterSummary,
    AuthenticationError,
    Tv,
    TVBalanceClient,
    TVBalanceError,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from . import TVBalanceConfigEntry

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=30)


class TVBalanceCoordinator(DataUpdateCoordinator[dict[str, Tv]]):
    """TVs by id. The Engine is the source of truth; this only mirrors it."""

    config_entry: TVBalanceConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TVBalanceConfigEntry, client: TVBalanceClient
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=POLL_INTERVAL
        )
        self.client = client
        self.adapters: dict[str, AdapterSummary] = {}

    async def _async_setup(self) -> None:
        try:
            self.adapters = {a.id: a for a in await self.client.adapters()}
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed(str(ex)) from ex
        except TVBalanceError as ex:
            raise UpdateFailed(str(ex)) from ex

    async def _async_update_data(self) -> dict[str, Tv]:
        try:
            tvs = await self.client.tvs()
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed(str(ex)) from ex
        except TVBalanceError as ex:
            raise UpdateFailed(str(ex)) from ex
        return {tv.id: tv for tv in tvs}
