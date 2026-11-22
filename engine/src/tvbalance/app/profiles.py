"""Profiles: switching a rule set on for the household, and finding the one in force.

A profile is an existing policy. It applies to every TV except those excluded when it was
switched on. Without a Pro license everything is still stored but ignored, so nothing is lost
when a license arrives or lapses.
"""

from __future__ import annotations

from datetime import datetime

from tvbalance.domain.profiles import (
    ActiveProfile,
    ProfileActivation,
    ProfileSource,
    resolve_profile,
)
from tvbalance.ports.services import Clock, Entitlements
from tvbalance.ports.storage import Storage


class ProfileService:
    def __init__(
        self, storage: Storage, clock: Clock, entitlements: Entitlements | None = None
    ) -> None:
        self._storage = storage
        self._clock = clock
        self._entitlements = entitlements  # ``None``: nothing is gated

    @property
    def effective(self) -> bool:
        """Whether profiles and the calendar currently take effect."""
        return self._entitlements is None or self._entitlements.is_pro()

    async def activate(
        self,
        policy_id: int,
        until: datetime,
        excluded_tv_ids: frozenset[str] = frozenset(),
        source: ProfileSource = ProfileSource.MANUAL,
    ) -> ProfileActivation:
        """Put the profile in force now. Any profile already in force ends."""
        now = self._clock.now()
        if until <= now:
            raise ValueError("a profile must end in the future")
        activation = ProfileActivation(policy_id, now, until, excluded_tv_ids, source)
        await self._storage.profiles.activate(activation, now)
        return activation

    async def stop(self) -> int:
        """End the profile in force; the calendar may still apply afterwards."""
        return await self._storage.profiles.stop(self._clock.now())

    async def active_for(self, tv_id: str, now: datetime) -> ActiveProfile | None:
        """The profile in force for ``tv_id``; ``now`` is aware, in the household's zone."""
        if not self.effective:
            return None
        activations = await self._storage.profiles.active(now)
        entries = tuple(record.entry for record in await self._storage.profiles.entries())
        return resolve_profile(now, tv_id, activations, entries)
