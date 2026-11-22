"""The Free/Pro gate: holds the license key and answers what the household may use.

The gate is runtime only. Anything configured beyond the plan stays saved but inert, and a license
that expires or stops verifying simply leaves the household on Free.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from tvbalance.infra.licensing import (
    TRUSTED_PUBLIC_KEYS,
    LicenseError,
    LicensePayload,
    verify_license,
)
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import SecretSettingsStore

log = logging.getLogger(__name__)

LICENSE_SECRET = "license.key"
FREE_MAX_TVS = 1
CHECK_INTERVAL = 60.0

LicenseStatus = Literal["none", "active", "expired", "invalid"]


class LicenseEvents(Protocol):
    async def publish(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class LicenseInfo:
    """What may be shown about the license; never the key itself."""

    status: LicenseStatus
    tier: Literal["free", "pro"]
    licensee: str | None
    expires_at: datetime | None
    max_tvs: int | None  # ``None``: unlimited


class LicenseService:
    """Implements the ``Entitlements`` port over a license key kept in the sealed secrets."""

    def __init__(
        self,
        secrets: SecretSettingsStore,
        events: LicenseEvents,
        clock: Clock,
        public_keys: Iterable[str] = TRUSTED_PUBLIC_KEYS,
        on_change: Callable[[], Awaitable[None]] | None = None,
        check_interval: float = CHECK_INTERVAL,
    ) -> None:
        self._secrets = secrets
        self._events = events
        self._clock = clock
        self._public_keys = tuple(public_keys)
        self._on_change = on_change
        self._interval = check_interval
        self._payload: LicensePayload | None = None
        self._stored = False
        self._announced: tuple[str, str] | None = None
        self._task: asyncio.Task[None] | None = None

    async def load(self) -> None:
        key = (await self._secrets.get(LICENSE_SECRET) or "").strip()
        self._stored = bool(key)
        self._payload = None
        if key:
            try:
                self._payload = verify_license(key, self._public_keys)
            except LicenseError as ex:
                log.warning("the stored license is not usable: %s", ex)
        self._announced = self._state()

    def status(self) -> LicenseStatus:
        if self._payload is None:
            return "invalid" if self._stored else "none"
        expires_at = self._payload.expires_at
        if expires_at is not None and self._clock.now() >= expires_at:
            return "expired"
        return "active"

    def is_pro(self) -> bool:
        return self.status() == "active"

    def max_tvs(self) -> int | None:
        return None if self.is_pro() else FREE_MAX_TVS

    def info(self) -> LicenseInfo:
        payload = self._payload
        return LicenseInfo(
            status=self.status(),
            tier="pro" if self.is_pro() else "free",
            licensee=payload.licensee if payload else None,
            expires_at=payload.expires_at if payload else None,
            max_tvs=self.max_tvs(),
        )

    async def activate(self, key: str) -> None:
        """Verify and keep ``key``; on ``LicenseError`` the current license stays as it was."""
        payload = verify_license(key, self._public_keys)
        if payload.expires_at is not None and self._clock.now() >= payload.expires_at:
            raise LicenseError("this license has already expired")
        await self._secrets.set(LICENSE_SECRET, key.strip())
        self._payload, self._stored = payload, True
        await self._announce()

    async def remove(self) -> None:
        await self._secrets.set(LICENSE_SECRET, "")
        self._payload, self._stored = None, False
        await self._announce()

    def _state(self) -> tuple[str, str]:
        return self.info().tier, self.status()

    async def _announce(self) -> None:
        """Publish ``license_changed`` and let the supervisor re-apply the limits."""
        state = self._announced = self._state()
        await self._events.publish(
            None, "license_changed", {"tier": state[0], "status": state[1]}, self._clock.now()
        )
        if self._on_change is not None:
            try:
                await self._on_change()
            except Exception:
                log.exception("applying the new license failed")

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            if self._state() != self._announced:
                await self._announce()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run(), name="license-expiry")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
