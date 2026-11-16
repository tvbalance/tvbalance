"""Shared helpers for the engine tests: a controllable clock, scripted TVs and a harness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from typing import Any

from fastapi.testclient import TestClient

from tvbalance.app.events import BusEvent
from tvbalance.app.session import SessionTimeouts
from tvbalance.app.status import SupervisorSettings
from tvbalance.domain.models import Action, Observation, Policy, Power, Schedule, TimeWindow
from tvbalance.sdk.errors import TVError, TVPairingError
from tvbalance.sdk.fake import FakeTV
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import AdapterConfig, AdapterInfo, Capability, Maturity

# A Tuesday evening: 18:00 in the household zone used by the tests (Europe/Rome).
T0 = datetime(2026, 11, 17, 17, 0, tzinfo=UTC)

FAST = SupervisorSettings(
    tick_interval=0.02,
    backoff_min=0.01,
    backoff_max=0.04,
    timeouts=SessionTimeouts(connect=0.2, observe=0.2, execute=0.2, inventory=0.2),
)

ALL_DAY = Schedule(windows={day: (TimeWindow(time(0), time(0)),) for day in range(7)})
OPEN = Policy(schedule=ALL_DAY, blocked_apps=frozenset({"tiktok"}))
CLOSED = Policy()  # an empty schedule blocks everything


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


ADMIN_PASSWORD = "correct horse battery"
CSRF_HEADER = "X-TVBalance-CSRF"


def sign_in_as_admin(client: TestClient, password: str = ADMIN_PASSWORD) -> None:
    """Create the admin account on a fresh engine; the client keeps the cookies and CSRF header."""
    response = client.post("/api/v1/auth/setup", json={"password": password})
    assert response.status_code == 201, response.text
    client.headers[CSRF_HEADER] = response.json()["csrf_token"]


def watching(app: str | None = "video") -> Observation:
    return Observation(observed_at=T0, power=Power.ON, foreground_app=app)


@dataclass
class ScriptedTV(FakeTV):
    """A FakeTV whose connection can be refused, dropped or hung on demand."""

    connect_error: TVError | None = None
    observe_error: TVError | None = None
    hang_execute: bool = False
    connect_calls: int = 0
    observe_calls: int = 0
    listeners: list[Callable[[], None]] = field(default_factory=list)

    async def connect(self) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        await super().connect()

    async def observe(self) -> Observation:
        self.observe_calls += 1
        if self.observe_error is not None:
            raise self.observe_error
        return await super().observe()

    async def execute(self, action: Action) -> None:
        if self.hang_execute:
            await asyncio.Event().wait()
        await super().execute(action)

    def on_change(self, callback: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(callback)
        return lambda: self.listeners.remove(callback)

    def changed(self) -> None:
        for listener in list(self.listeners):
            listener()


def pairing_rejected() -> TVPairingError:
    return TVPairingError("the TV refused the stored key")


def plugin_for(
    tv: FakeTV, capabilities: frozenset[Capability] | None = None, adapter_id: str = "fake"
) -> AdapterPlugin:
    caps = frozenset(Capability) if capabilities is None else capabilities

    def factory(config: AdapterConfig) -> Any:
        return tv

    return AdapterPlugin(
        info=AdapterInfo(adapter_id, "Fake", "Fake TV", Maturity.EXPERIMENTAL, caps),
        factory=factory,
    )


async def eventually(check: Callable[[], bool | Awaitable[bool]], within: float = 2.0) -> None:
    """Poll until ``check`` holds; fail the test with a clear message otherwise."""
    async with asyncio.timeout(within):
        while True:
            result = check()
            if await result if isinstance(result, Awaitable) else result:
                return
            await asyncio.sleep(0.005)


def kinds(queue: asyncio.Queue[BusEvent]) -> list[str]:
    """Drain ``queue`` and return the event types, oldest first."""
    found: list[str] = []
    while not queue.empty():
        found.append(queue.get_nowait().type)
    return found
