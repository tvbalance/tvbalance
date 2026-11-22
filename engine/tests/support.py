"""Shared helpers for the engine tests: a controllable clock, scripted TVs and a harness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from time import monotonic, sleep
from typing import Any

from fastapi.testclient import TestClient

from tvbalance.app.events import BusEvent
from tvbalance.app.session import SessionTimeouts
from tvbalance.app.status import SupervisorSettings
from tvbalance.domain.models import Action, Observation, Policy, Power, Schedule, TimeWindow
from tvbalance.infra.licensing import generate_keypair, sign_license
from tvbalance.sdk.errors import TVError, TVPairingError
from tvbalance.sdk.fake import FakeTV
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import AdapterConfig, AdapterInfo, Capability, Maturity, PairingState

# A Tuesday evening: 18:00 in the household zone used by the tests (Europe/Rome).
T0 = datetime(2026, 11, 17, 17, 0, tzinfo=UTC)

# A signing key pair for tests: pass ``license_public_keys=(LICENSE_PUBLIC,)`` to ``create_app``.
LICENSE_PRIVATE, LICENSE_PUBLIC = generate_keypair()


def license_key(expires_at: datetime | None = None, licensee: str = "Rossi") -> str:
    """A Pro license signed with the test key."""
    return sign_license(
        {
            "v": 1,
            "product": "tvbalance",
            "tier": "pro",
            "license_id": "test-license",
            "licensee": licensee,
            "issued_at": T0.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
        LICENSE_PRIVATE,
    )


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


def seed_tv(
    client: TestClient, adapter: str = "fake", name: str = "Living room", host: str = "tv.local"
) -> str:
    """Pair a TV straight in the storage of the running app (the API has no pairing yet)."""
    storage = client.app.state.storage  # type: ignore[attr-defined]
    assert client.portal is not None
    record = client.portal.call(storage.tvs.add, adapter, name, host, {"client_key": "k"})
    return str(record.id)


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


class ScriptedPairing:
    """A pairing flow that walks through ``outcomes`` one poll at a time, then stays where it is."""

    def __init__(self, outcomes: list[PairingState], key: str = "paired-key") -> None:
        self.outcomes = list(outcomes)
        self.key = key
        self.state = PairingState.IDLE
        self.cancelled = False

    async def start(self) -> PairingState:
        self.state = PairingState.WAITING_FOR_USER
        return self.state

    async def poll(self) -> PairingState:
        await asyncio.sleep(0)
        if self.outcomes:
            self.state = self.outcomes.pop(0)
        return self.state

    def credentials(self) -> dict[str, str]:
        return {"client_key": self.key} if self.state is PairingState.COMPLETED else {}

    async def cancel(self) -> None:
        self.cancelled = True


@dataclass
class PairableTV(ScriptedTV):
    """A ScriptedTV that pairs the way ``flow`` says."""

    flow: ScriptedPairing = field(default_factory=lambda: ScriptedPairing([PairingState.COMPLETED]))

    def pairing(self) -> ScriptedPairing:  # type: ignore[override]
        return self.flow


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


def wait_connected(client: TestClient, tv_id: str) -> None:
    assert client.portal is not None
    client.portal.call(client.app.state.supervisor.refresh)  # type: ignore[attr-defined]
    deadline = monotonic() + 3
    while monotonic() < deadline:
        status = client.get(f"/api/v1/tvs/{tv_id}").json()["status"]
        if status is not None and status["connected"]:
            return
        sleep(0.02)
    raise AssertionError("the TV never connected")
