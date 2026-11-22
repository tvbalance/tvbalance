from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest
from support import T0, FakeClock

from tvbalance.app.licensing import LICENSE_SECRET, LicenseService
from tvbalance.infra.licensing import LicenseError, generate_keypair, sign_license


class MemorySecrets:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


class RecordingBus:
    def __init__(self) -> None:
        self.events: list[tuple[str | None, str, dict[str, Any]]] = []

    async def publish(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None:
        self.events.append((tv_id, event_type, payload))


PRIVATE, PUBLIC = generate_keypair()


def _key(expires_in: timedelta | None = None, **changes: object) -> str:
    payload: dict[str, object] = {
        "v": 1,
        "product": "tvbalance",
        "tier": "pro",
        "license_id": "id-1",
        "licensee": "Rossi",
        "issued_at": T0.isoformat(),
        "expires_at": None if expires_in is None else (T0 + expires_in).isoformat(),
    }
    return sign_license({**payload, **changes}, PRIVATE)


class Harness:
    def __init__(self) -> None:
        self.secrets, self.bus, self.clock = MemorySecrets(), RecordingBus(), FakeClock()
        self.changes = 0

        async def changed() -> None:
            self.changes += 1

        self.service = LicenseService(
            self.secrets, self.bus, self.clock, (PUBLIC,), changed, check_interval=0.01
        )


async def test_starts_free_without_a_key() -> None:
    h = Harness()
    await h.service.load()
    info = h.service.info()
    assert (info.status, info.tier, info.licensee) == ("none", "free", None)
    assert not h.service.is_pro() and h.service.max_tvs() == 1


async def test_activation_unlocks_pro_and_persists() -> None:
    h = Harness()
    await h.service.load()
    await h.service.activate(f"  {_key()} ")
    assert h.service.is_pro() and h.service.max_tvs() is None
    info = h.service.info()
    assert (info.status, info.tier, info.licensee, info.expires_at) == (
        "active",
        "pro",
        "Rossi",
        None,
    )
    assert h.changes == 1
    assert h.bus.events == [(None, "license_changed", {"tier": "pro", "status": "active"})]

    again = LicenseService(h.secrets, h.bus, h.clock, (PUBLIC,), None)
    await again.load()
    assert again.is_pro()


async def test_bad_key_is_refused_and_keeps_the_current_license() -> None:
    h = Harness()
    await h.service.load()
    await h.service.activate(_key())
    with pytest.raises(LicenseError):
        await h.service.activate("garbage")
    assert h.service.is_pro() and h.changes == 1


async def test_already_expired_key_is_refused() -> None:
    h = Harness()
    await h.service.load()
    with pytest.raises(LicenseError, match="expired"):
        await h.service.activate(_key(expires_in=timedelta(days=-1)))
    assert not h.service.is_pro() and LICENSE_SECRET not in h.secrets.values


async def test_removal_goes_back_to_free() -> None:
    h = Harness()
    await h.service.load()
    await h.service.activate(_key())
    await h.service.remove()
    assert not h.service.is_pro() and h.service.info().status == "none"
    assert h.changes == 2
    assert h.bus.events[-1] == (None, "license_changed", {"tier": "free", "status": "none"})


async def test_stored_key_that_no_longer_verifies_is_invalid_not_fatal() -> None:
    h = Harness()
    h.secrets.values[LICENSE_SECRET] = _key()
    other = LicenseService(h.secrets, h.bus, h.clock, (generate_keypair()[1],), None)
    await other.load()
    assert other.info().status == "invalid" and not other.is_pro()


async def test_expiry_is_judged_against_the_clock() -> None:
    h = Harness()
    await h.service.load()
    await h.service.activate(_key(expires_in=timedelta(days=1)))
    assert h.service.is_pro()
    h.clock.advance(days=2)
    assert not h.service.is_pro() and h.service.info().status == "expired"
    assert h.service.max_tvs() == 1


async def test_expiry_task_announces_the_fall_back_to_free() -> None:
    h = Harness()
    await h.service.load()
    await h.service.activate(_key(expires_in=timedelta(days=1)))
    h.service.start()
    try:
        await asyncio.sleep(0.05)
        assert h.changes == 1  # nothing changes while the license is valid
        h.clock.advance(days=2)
        for _ in range(100):
            if h.changes == 2:
                break
            await asyncio.sleep(0.01)
    finally:
        await h.service.stop()
    assert h.changes == 2
    assert h.bus.events[-1] == (None, "license_changed", {"tier": "free", "status": "expired"})


async def test_changed_callback_failure_does_not_break_activation() -> None:
    h = Harness()

    async def boom() -> None:
        raise RuntimeError("nope")

    service = LicenseService(h.secrets, h.bus, h.clock, (PUBLIC,), boom)
    await service.load()
    await service.activate(_key())
    assert service.is_pro()
