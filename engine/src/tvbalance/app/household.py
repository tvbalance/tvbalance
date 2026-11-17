"""The household's own clock: the stored time zone decides when a day starts and ends."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo

from tvbalance.ports.services import Clock
from tvbalance.ports.storage import SettingsStore

log = logging.getLogger(__name__)


async def household_now(settings: SettingsStore, clock: Clock) -> datetime:
    """The current time in the household's zone (the system zone when none is set)."""
    zone: tzinfo | None = None
    name = await settings.get("timezone")
    if name:
        try:
            zone = ZoneInfo(str(name))
        except (KeyError, ValueError, OSError):
            log.warning("unknown timezone %r: using the system zone", name)
    return clock.now().astimezone(zone)


def next_midnight(now: datetime) -> datetime:
    """The start of the next local day, in the zone of ``now``."""
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=now.tzinfo)
