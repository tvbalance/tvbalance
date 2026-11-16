"""Pure translation of webOS SSAP payloads into TVBalance types."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tvbalance.domain.models import Power
from tvbalance.sdk.types import AppInfo, ChannelInfo, InputInfo

LIVETV_APP_ID = "com.webos.app.livetv"
HDMI_PREFIX = "com.webos.app.hdmi"

_STANDBY_STATES = {"Screen Off", "Active Standby", "Suspend"}


def power_from_state(state: str | None) -> Power:
    """Map a webOS power state. With Quick Start+ the socket stays open in standby."""
    if state == "Power Off":
        return Power.OFF
    if state in _STANDBY_STATES:
        return Power.STANDBY
    return Power.ON


def _rows(rows: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Dict rows only: a TV in standby can return strings or nulls in its lists."""
    return [r for r in rows or () if isinstance(r, dict)]


def split_foreground(
    app_id: str | None, input_rows: Iterable[Any] | None
) -> tuple[str | None, str | None, bool]:
    """``(foreground_app, input_id, is_livetv)`` for the app currently in front.

    Live TV is always the foreground app while watching a channel, so it is reported as a
    channel (by the caller) rather than as an app; HDMI apps are reported as inputs.
    """
    if not app_id:
        return None, None, False
    if app_id == LIVETV_APP_ID:
        return None, None, True
    if app_id.startswith(HDMI_PREFIX):
        for row in _rows(input_rows):
            if row.get("appId") == app_id and row.get("id"):
                return None, str(row["id"]), False
        return None, app_id, False
    return app_id, None, False


def app_infos(rows: Iterable[Any] | None) -> list[AppInfo]:
    """Launch points as apps. Icons are kept raw: the TV serves them over a self-signed https."""
    return [
        AppInfo(str(r["id"]), str(r.get("title") or r["id"]), r.get("icon") or None)
        for r in _rows(rows)
        if r.get("id")
    ]


def input_infos(rows: Iterable[Any] | None) -> list[InputInfo]:
    return [
        InputInfo(str(r["id"]), str(r.get("label") or r["id"])) for r in _rows(rows) if r.get("id")
    ]


def channel_infos(rows: Iterable[Any] | None) -> list[ChannelInfo]:
    return [
        ChannelInfo(
            str(r["channelId"]),
            str(r.get("channelName") or r["channelId"]),
            str(r["channelNumber"]) if r.get("channelNumber") else None,
        )
        for r in _rows(rows)
        if r.get("channelId")
    ]
