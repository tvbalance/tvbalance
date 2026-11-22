"""TvWorker: supervises one TV. Observe, count usage, apply the rules, act, report.

``run`` never dies of its own accord: a TV that vanishes, a hung adapter or a database hiccup
only delays the next look. Only cancellation stops it.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timedelta

from tvbalance.app.events import EventBus, to_record
from tvbalance.app.household import household_now
from tvbalance.app.messages import localize
from tvbalance.app.profiles import ProfileService
from tvbalance.app.session import TVSession
from tvbalance.app.status import Inventory, ProfileInfo, SupervisorSettings, TvStatus
from tvbalance.domain.budget import accrue, remaining_seconds
from tvbalance.domain.enforcement import EnforcementState, step
from tvbalance.domain.models import Decision, Observation, Policy, Power, Usage
from tvbalance.domain.rules import evaluate
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import PolicyRecord, Storage, TvRecord
from tvbalance.sdk.errors import TVError, TVPairingError, TVTimeoutError
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import AdapterConfig, Capability

log = logging.getLogger(__name__)


INVENTORY_TTL = timedelta(minutes=5)


def _nothing() -> None:
    pass


class TvWorker:
    def __init__(
        self,
        record: TvRecord,
        plugin: AdapterPlugin,
        storage: Storage,
        bus: EventBus,
        clock: Clock,
        settings: SupervisorSettings | None = None,
        profiles: ProfileService | None = None,
    ) -> None:
        self._record = record
        self._plugin = plugin
        self._storage = storage
        self._bus = bus
        self._clock = clock
        self._settings = settings or SupervisorSettings()
        self._profiles = profiles
        self._profile: ProfileInfo | None = None
        self._session: TVSession | None = None
        self._unsubscribe: Callable[[], None] = _nothing
        self._wake = asyncio.Event()
        self._state: EnforcementState | None = None
        self._last_tick: datetime | None = None
        self._last_obs: Observation | None = None
        self._outage_reported = False
        self._status = TvStatus(record.id)
        self._inventory: tuple[datetime, Inventory] | None = None

    @property
    def status(self) -> TvStatus:
        return self._status

    @property
    def tv_id(self) -> str:
        return self._record.id

    # -- connection -------------------------------------------------------------------------

    async def connect(self) -> bool:
        """Open a session. ``False`` when the TV cannot be used right now."""
        if self._record.needs_pairing:
            await self._pairing_lost("stored credentials cannot be read")
            return False
        config = AdapterConfig(self._record.host, self._record.credentials)
        try:
            adapter = self._plugin.factory(config)
            session = TVSession(adapter, self._settings.timeouts)
            await session.connect()
        except TVPairingError as ex:
            await self._pairing_lost(str(ex))
            return False
        except TVError as ex:
            log.info("TV %s unreachable: %s", self._record.id, ex)
            await self._drop_session()
            return False
        self._session = session
        self._last_tick = None  # time spent offline is never billed
        self._subscribe(adapter)
        self._set_status(connected=True, pairing_required=False)
        if self._outage_reported:
            self._outage_reported = False
            await self._publish("tv_reachable", {})
        return True

    def _subscribe(self, adapter: object) -> None:
        if Capability.PUSH_UPDATES not in self._plugin.info.capabilities:
            return
        on_change = getattr(adapter, "on_change", None)
        if on_change is None:
            return
        loop = asyncio.get_running_loop()
        self._unsubscribe = on_change(lambda: loop.call_soon_threadsafe(self._wake.set))

    async def inventory(self) -> Inventory:
        """Apps, inputs and channels of the connected TV, listed at most every few minutes.

        Raises ``TVError`` when there is no session or the TV fails to answer.
        """
        session = self._session
        if session is None:
            raise TVError("the TV is not connected")
        now = self._clock.now()
        if self._inventory is not None and now - self._inventory[0] < INVENTORY_TTL:
            return self._inventory[1]
        caps = self._plugin.info.capabilities
        listed = Inventory(
            apps=tuple(await session.list_apps()) if Capability.LIST_APPS in caps else (),
            inputs=tuple(await session.list_inputs())
            if caps & {Capability.CURRENT_INPUT, Capability.SET_INPUT}
            else (),
            channels=tuple(await session.list_channels())
            if caps & {Capability.LIVE_CHANNEL, Capability.SET_CHANNEL}
            else (),
        )
        self._inventory = (now, listed)
        return listed

    async def _drop_session(self) -> None:
        session, self._session = self._session, None
        self._inventory = None
        with suppress(Exception):
            self._unsubscribe()
        self._unsubscribe = _nothing
        self._set_status(connected=False)
        if session is not None:
            with suppress(TVError):
                await session.close()

    async def _pairing_lost(self, reason: str) -> None:
        await self._drop_session()
        self._set_status(pairing_required=True)
        await self._publish("pairing_lost", {"reason": reason})

    async def _lost(self, reason: str) -> None:
        reported = self._last_obs is not None and self._last_obs.power is Power.ON
        await self._drop_session()
        if reported and not self._outage_reported:
            self._outage_reported = True
            await self._publish("tv_unreachable", {"reason": reason})
        self._last_obs = None

    # -- one look at the TV -----------------------------------------------------------------

    async def tick(self) -> None:
        session = self._session
        if session is None:
            return
        try:
            obs = await session.observe()
        except TVError as ex:
            await self._lost(str(ex))
            return
        now = await self._local_now()
        self._last_obs = obs

        record = await self._storage.tvs.get(self._record.id)
        if record is not None:
            self._record = record
        policy_record = await self._rules(now)
        policy = Policy() if policy_record is None else policy_record.policy

        usage = await self._storage.usage.get(self._record.id, now.date())
        if self._last_tick is not None:
            billed = accrue(usage, self._last_tick, now, obs, policy)
            delta = billed.watched_seconds - usage.watched_seconds
            if billed.day == usage.day and delta > 0:
                await self._storage.usage.add_watched(self._record.id, now.date(), delta)
                usage = billed
        self._last_tick = now
        if usage.day != now.date():
            usage = Usage(day=now.date())

        if policy_record is None:  # no rules assigned: observe only
            self._set_status(observation=obs, usage=usage, policy=policy, at=now)
            return

        overrides = await self._storage.overrides.active(self._record.id, now)
        decision = evaluate(now, obs, policy, usage, overrides)
        if self._state is None:
            self._state = await self._storage.enforcement.load(self._record.id)
        result = step(self._state, now, decision, obs, self._plugin.info.capabilities, policy)
        if result.state != self._state:
            self._state = result.state
            await self._storage.enforcement.save(self._record.id, result.state)

        language = str(await self._storage.settings.get("language", "en"))
        for action in result.actions:
            try:
                await session.execute(localize(action, language))
            except TVTimeoutError as ex:
                log.warning("TV %s: %s", self._record.id, ex)
                await self._drop_session()
                break
            except TVError as ex:
                log.warning("TV %s: could not run %s: %s", self._record.id, action, ex)
        for event in result.events:
            event_type, payload = to_record(event)
            await self._publish(event_type, payload)
        self._set_status(observation=obs, decision=decision, usage=usage, policy=policy, at=now)

    async def _rules(self, now: datetime) -> PolicyRecord | None:
        """The profile in force when there is one, else the rules assigned to the TV."""
        found = (
            None
            if self._profiles is None
            else await self._profiles.active_for(self._record.id, now)
        )
        profile = None if found is None else await self._storage.policies.get(found.policy_id)
        if found is not None and profile is not None:
            await self._profile_changed(
                ProfileInfo(profile.id, profile.name, found.until, found.source)
            )
            return profile
        await self._profile_changed(None)
        if self._record.policy_id is None:
            return None
        return await self._storage.policies.get(self._record.policy_id)

    async def _profile_changed(self, now_in_force: ProfileInfo | None) -> None:
        """Report a profile coming into or going out of force, once each."""
        before = self._profile
        old_id = None if before is None else before.policy_id
        new_id = None if now_in_force is None else now_in_force.policy_id
        if before is not None and old_id != new_id:
            await self._publish(
                "profile_ended", {"policy_id": before.policy_id, "name": before.name}
            )
        if now_in_force is not None and old_id != new_id:
            await self._publish(
                "profile_started",
                {
                    "policy_id": now_in_force.policy_id,
                    "name": now_in_force.name,
                    "until": now_in_force.until.isoformat(),
                    "source": now_in_force.source.value,
                },
            )
        self._profile = now_in_force

    async def _local_now(self) -> datetime:
        return await household_now(self._storage.settings, self._clock)

    def nudge(self) -> None:
        """Look at the TV now instead of at the next tick (an override or bonus just changed)."""
        self._wake.set()

    # -- loop -------------------------------------------------------------------------------

    async def run(self) -> None:
        backoff = self._settings.backoff_min
        failing = False
        try:
            while True:
                try:
                    if self._session is None:
                        if self._status.pairing_required:
                            await asyncio.Event().wait()  # parked until the supervisor refreshes
                        if await self.connect():
                            backoff = self._settings.backoff_min
                        else:
                            if self._status.pairing_required:
                                continue
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, self._settings.backoff_max)
                            continue
                    await self.tick()
                    failing = False
                except asyncio.CancelledError:
                    raise
                except Exception:
                    if not failing:
                        log.exception("supervision of TV %s failed; retrying", self._record.id)
                    failing = True
                await self._sleep()
        finally:
            await asyncio.shield(self._drop_session())

    async def _sleep(self) -> None:
        with suppress(TimeoutError):
            async with asyncio.timeout(self._settings.tick_interval):
                await self._wake.wait()
        self._wake.clear()

    # -- reporting --------------------------------------------------------------------------

    async def _publish(self, event_type: str, payload: dict[str, object]) -> None:
        await self._bus.publish(self._record.id, event_type, payload, self._clock.now())

    def _set_status(
        self,
        *,
        connected: bool | None = None,
        pairing_required: bool | None = None,
        observation: Observation | None = None,
        decision: Decision | None = None,
        usage: Usage | None = None,
        policy: Policy | None = None,
        at: datetime | None = None,
    ) -> None:
        old = self._status
        self._status = TvStatus(
            tv_id=old.tv_id,
            connected=old.connected if connected is None else connected,
            pairing_required=old.pairing_required if pairing_required is None else pairing_required,
            observation=old.observation if observation is None else observation,
            decision=old.decision if decision is None else decision,
            watched_seconds=old.watched_seconds if usage is None else usage.watched_seconds,
            remaining_seconds=(
                old.remaining_seconds
                if usage is None or policy is None
                else remaining_seconds(policy, usage)
            ),
            updated_at=old.updated_at if at is None else at,
            active_profile=self._profile,
        )
