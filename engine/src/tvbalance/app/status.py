"""Supervisor settings and the live status of a supervised TV."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from tvbalance.app.session import SessionTimeouts
from tvbalance.domain.models import Decision, Observation
from tvbalance.sdk.types import AppInfo, ChannelInfo, InputInfo


@dataclass(frozen=True, slots=True)
class SupervisorSettings:
    tick_interval: float = 2.0  # longest wait between two looks at a TV
    backoff_min: float = 2.0  # first wait before reconnecting; doubles up to ``backoff_max``
    backoff_max: float = 60.0
    timeouts: SessionTimeouts = field(default_factory=SessionTimeouts)


@dataclass(frozen=True, slots=True)
class Inventory:
    """What a TV offers that a rule can name; empty where the adapter cannot list it."""

    apps: tuple[AppInfo, ...] = ()
    inputs: tuple[InputInfo, ...] = ()
    channels: tuple[ChannelInfo, ...] = ()


@dataclass(frozen=True, slots=True)
class TvStatus:
    tv_id: str
    connected: bool = False
    pairing_required: bool = False
    observation: Observation | None = None
    decision: Decision | None = None
    watched_seconds: int = 0
    remaining_seconds: int | None = None  # ``None``: no daily budget
    updated_at: datetime | None = None
