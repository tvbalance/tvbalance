"""Diagnostics download: engine info with secrets redacted."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TVBalanceConfigEntry
from .const import CONF_TOKEN

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TVBalanceConfigEntry
) -> dict[str, Any]:
    info = await entry.runtime_data.info()
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "engine": asdict(info),
    }
