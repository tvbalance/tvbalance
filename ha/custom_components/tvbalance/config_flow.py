"""Config flow: connect to a TVBalance Engine by URL (and optional API token)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from tvbalance_client import TVBalanceClient, TVBalanceConnectionError, TVBalanceError

from .const import CONF_TOKEN, CONF_URL, DOMAIN


class TVBalanceConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            token = user_input.get(CONF_TOKEN) or None
            client = TVBalanceClient(url, token, session=async_get_clientsession(self.hass))
            try:
                await client.info()
            except TVBalanceConnectionError:
                errors["base"] = "cannot_connect"
            except TVBalanceError:
                errors["base"] = "invalid_response"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                data = {CONF_URL: url}
                if token:
                    data[CONF_TOKEN] = token
                return self.async_create_entry(title=f"TVBalance ({url})", data=data)

        schema = vol.Schema({vol.Required(CONF_URL): str, vol.Optional(CONF_TOKEN): str})
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
