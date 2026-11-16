"""Adapter SDK value types: capabilities, adapter metadata and TV inventory rows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Capability(StrEnum):
    FOREGROUND_APP = "foreground_app"
    LIST_APPS = "list_apps"
    LAUNCH_APP = "launch_app"
    GO_HOME = "go_home"
    CURRENT_INPUT = "current_input"
    SET_INPUT = "set_input"
    LIVE_CHANNEL = "live_channel"
    SET_CHANNEL = "set_channel"
    PROGRAM_INFO = "program_info"
    ON_SCREEN_MESSAGE = "on_screen_message"
    POWER_OFF = "power_off"
    WAKE = "wake"
    PUSH_UPDATES = "push_updates"


class Maturity(StrEnum):
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True, slots=True)
class AdapterInfo:
    id: str
    brand: str
    display_name: str
    maturity: Maturity
    capabilities: frozenset[Capability]
    testing_only: bool = False  # hidden from end users (reference/fake adapters)


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    """What an adapter needs to talk to one TV."""

    host: str
    credentials: dict[str, str]


@dataclass(frozen=True, slots=True)
class DiscoveredDevice:
    adapter_id: str
    host: str
    name: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class AppInfo:
    app_id: str
    name: str
    icon_url: str | None = None


@dataclass(frozen=True, slots=True)
class InputInfo:
    input_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ChannelInfo:
    channel_id: str
    name: str
    number: str | None = None


class PairingState(StrEnum):
    IDLE = "idle"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"
