"""Pure domain types. No I/O, no clocks, no framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
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
    """An allowed viewing window (start inclusive, end exclusive).

    ``start > end`` crosses midnight and belongs to the day it starts on;
    ``start == end`` covers 24 hours.
    """

    start: time
    end: time


@dataclass(frozen=True, slots=True)
class Schedule:
    """Allowed windows per weekday (0 = Monday) with per-date exceptions.

    A day without windows is fully blocked. ``special_days`` replaces the weekday rule for a date;
    an empty tuple blocks that date.
    """

    windows: dict[int, tuple[TimeWindow, ...]] = field(default_factory=dict)
    special_days: dict[date, tuple[TimeWindow, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AppTarget:
    app_id: str


@dataclass(frozen=True, slots=True)
class InputTarget:
    input_id: str


@dataclass(frozen=True, slots=True)
class ChannelTarget:
    channel_id: str


@dataclass(frozen=True, slots=True)
class HomeTarget:
    pass


type Target = AppTarget | InputTarget | ChannelTarget | HomeTarget


@dataclass(frozen=True, slots=True)
class EscalationSettings:
    """Timings and safeguards of the enforcement ladder."""

    debounce: timedelta = timedelta(seconds=3)
    grace: timedelta = timedelta(seconds=15)
    power_off_cap: int = 3
    cap_window: timedelta = timedelta(minutes=5)
    cap_pause: timedelta = timedelta(minutes=10)
    message_repeat: timedelta = timedelta(seconds=60)


@dataclass(frozen=True, slots=True)
class Policy:
    schedule: Schedule = field(default_factory=Schedule)
    daily_budget_minutes: int | None = None
    blocked_apps: frozenset[str] = frozenset()
    blocked_inputs: frozenset[str] = frozenset()
    blocked_channels: frozenset[str] = frozenset()
    allow_list_apps: frozenset[str] | None = None
    always_allowed_apps: frozenset[str] = frozenset()
    always_allowed_inputs: frozenset[str] = frozenset()
    always_allowed_channels: frozenset[str] = frozenset()
    fallback: Target | None = None
    warn_at_minutes: tuple[int, ...] = (10, 5)
    escalation: EscalationSettings = field(default_factory=EscalationSettings)


@dataclass(frozen=True, slots=True)
class Usage:
    """Viewing time consumed so far on one local calendar day."""

    day: date
    watched_seconds: int = 0
    bonus_minutes: int = 0


@dataclass(frozen=True, slots=True)
class Override:
    """A parent's temporary decision: ``allow`` lifts time limits, else everything is blocked."""

    allow: bool
    until: datetime
    created_at: datetime


class LimitKind(StrEnum):
    WINDOW = "window"
    BUDGET = "budget"
    OVERRIDE = "override"


class BlockReason(StrEnum):
    OUTSIDE_WINDOW = "outside_window"
    BUDGET_EXHAUSTED = "budget_exhausted"
    APP_BLOCKED = "app_blocked"
    INPUT_BLOCKED = "input_blocked"
    CHANNEL_BLOCKED = "channel_blocked"
    OVERRIDE = "override"

    @property
    def is_time_limit(self) -> bool:
        return self in (BlockReason.OUTSIDE_WINDOW, BlockReason.BUDGET_EXHAUSTED)

    @property
    def is_time_based(self) -> bool:
        """Blocks about *when* the TV may be used (limits and parent overrides), not *what*."""
        return self.is_time_limit or self is BlockReason.OVERRIDE


@dataclass(frozen=True, slots=True)
class Allow:
    pass


@dataclass(frozen=True, slots=True)
class Warn:
    minutes_left: int
    limit: LimitKind


@dataclass(frozen=True, slots=True)
class Block:
    reason: BlockReason


type Decision = Allow | Warn | Block


class MessageKind(StrEnum):
    TIME_WARNING = "time_warning"
    TIME_UP = "time_up"
    CONTENT_BLOCKED = "content_blocked"
    POWERING_OFF = "powering_off"


@dataclass(frozen=True, slots=True)
class ShowMessage:
    """An on-screen notice. The domain names the message; localized text is rendered elsewhere."""

    kind: MessageKind
    minutes_left: int | None = None


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


class EnforcementLevel(StrEnum):
    """Rungs of the escalation ladder, mildest first."""

    NOTIFY = "notify"
    REDIRECT = "redirect"
    POWER_OFF = "power_off"


@dataclass(frozen=True, slots=True)
class TimeWarning:
    minutes_left: int
    limit: LimitKind


@dataclass(frozen=True, slots=True)
class Blocked:
    reason: BlockReason


@dataclass(frozen=True, slots=True)
class Redirected:
    action: Action


@dataclass(frozen=True, slots=True)
class PoweredOff:
    pass


@dataclass(frozen=True, slots=True)
class EnforcementPaused:
    """Power-off cap reached: enforcement stands down until ``until``."""

    until: datetime


@dataclass(frozen=True, slots=True)
class EnforcementUnavailable:
    """The TV cannot perform any rung that would stop the viewing."""

    reason: BlockReason


type DomainEvent = (
    TimeWarning | Blocked | Redirected | PoweredOff | EnforcementPaused | (EnforcementUnavailable)
)
