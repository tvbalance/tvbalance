"""Pure domain types. No I/O, no clocks, no framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum


class Power(StrEnum):
    ON = "on"
    STANDBY = "standby"
    OFF = "off"


@dataclass(frozen=True, slots=True)
class Observation:
    """What the TV reports right now."""

    observed_at: datetime
    power: Power
    foreground_app: str | None = None
    input_id: str | None = None
    channel_id: str | None = None
    program_title: str | None = None


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """An allowed viewing window within a single day (start inclusive, end exclusive)."""

    start: time
    end: time


@dataclass(frozen=True, slots=True)
class Schedule:
    """Allowed windows per weekday (0 = Monday). A day without windows is fully blocked."""

    windows: dict[int, tuple[TimeWindow, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Policy:
    schedule: Schedule = field(default_factory=Schedule)
    daily_budget_minutes: int | None = None
    blocked_apps: frozenset[str] = frozenset()
    blocked_inputs: frozenset[str] = frozenset()
    blocked_channels: frozenset[str] = frozenset()
    allow_list_apps: frozenset[str] | None = None
    warn_at_minutes: tuple[int, ...] = (10, 5)


@dataclass(frozen=True, slots=True)
class Usage:
    """Viewing time consumed so far in the current day."""

    minutes_today: int = 0
    bonus_minutes: int = 0


@dataclass(frozen=True, slots=True)
class Override:
    """A parent's temporary decision."""

    allow: bool
    until: datetime


class BlockReason(StrEnum):
    OUTSIDE_WINDOW = "outside_window"
    BUDGET_EXHAUSTED = "budget_exhausted"
    APP_BLOCKED = "app_blocked"
    INPUT_BLOCKED = "input_blocked"
    CHANNEL_BLOCKED = "channel_blocked"
    OVERRIDE = "override"


@dataclass(frozen=True, slots=True)
class Allow:
    pass


@dataclass(frozen=True, slots=True)
class Warn:
    minutes_left: int


@dataclass(frozen=True, slots=True)
class Block:
    reason: BlockReason


type Decision = Allow | Warn | Block


@dataclass(frozen=True, slots=True)
class ShowMessage:
    text: str


@dataclass(frozen=True, slots=True)
class GoHome:
    pass


@dataclass(frozen=True, slots=True)
class LaunchApp:
    app_id: str


@dataclass(frozen=True, slots=True)
class SetInput:
    input_id: str


@dataclass(frozen=True, slots=True)
class SetChannel:
    channel_id: str


@dataclass(frozen=True, slots=True)
class PowerOff:
    pass


type Action = ShowMessage | GoHome | LaunchApp | SetInput | SetChannel | PowerOff
