"""Profiles: a rule set switched on for the household, by hand or by the calendar.

Everything can be saved on any plan; the ``effective`` flag says whether it is applied.
"""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from tvbalance.api.deps import (
    CanAdmin,
    CanControl,
    CanRead,
    get_clock,
    get_profiles,
    get_storage,
    get_supervisor,
)
from tvbalance.api.errors import not_found
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.api.schemas.profiles import (
    ActivateRequest,
    ActivationOut,
    ActiveProfileOut,
    CalendarEntryDoc,
    CalendarEntryOut,
    CalendarOut,
    DatedEntryDoc,
    DatedEntryOut,
    WeeklyEntryDoc,
    WeeklyEntryOut,
)
from tvbalance.app.household import household_now, next_midnight
from tvbalance.app.profiles import ProfileService
from tvbalance.app.supervisor import Supervisor
from tvbalance.domain.profiles import CalendarEntry, DatedEntry, ProfileActivation, WeeklyEntry
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1", tags=["profiles"])

StorageDep = Annotated[Storage, Depends(get_storage)]
SupervisorDep = Annotated[Supervisor, Depends(get_supervisor)]
ProfilesDep = Annotated[ProfileService, Depends(get_profiles)]
ClockDep = Annotated[Clock, Depends(get_clock)]


async def _check_references(storage: Storage, policy_id: int, tv_ids: list[str]) -> str:
    """The policy's name; a 404 when the policy or any named TV does not exist."""
    record = await storage.policies.get(policy_id)
    if record is None:
        raise not_found("policy")
    known = {tv.id for tv in await storage.tvs.list()}
    if any(tv_id not in known for tv_id in tv_ids):
        raise not_found("TV")
    return record.name


async def _nudge_all(storage: Storage, supervisor: Supervisor) -> None:
    for tv in await storage.tvs.list():
        supervisor.nudge(tv.id)


def _activation_out(activation: ProfileActivation, name: str) -> ActivationOut:
    return ActivationOut(
        policy_id=activation.policy_id,
        name=name,
        starts_at=activation.starts_at,
        ends_at=activation.ends_at,
        excluded_tv_ids=sorted(activation.excluded_tv_ids),
        source=activation.source,
    )


@router.get("/profiles/active", response_model=ActiveProfileOut, responses=AUTH_ERRORS)
async def get_active(
    _: CanRead, storage: StorageDep, profiles: ProfilesDep, clock: ClockDep
) -> ActiveProfileOut:
    live = await storage.profiles.active(clock.now())
    if not live:
        return ActiveProfileOut(effective=profiles.effective, activation=None)
    newest = live[-1]
    record = await storage.policies.get(newest.policy_id)
    name = record.name if record else ""
    return ActiveProfileOut(effective=profiles.effective, activation=_activation_out(newest, name))


@router.post("/profiles/active", response_model=ActivationOut, responses=NOT_FOUND_ERRORS)
async def activate(
    body: ActivateRequest,
    _: CanControl,
    storage: StorageDep,
    supervisor: SupervisorDep,
    profiles: ProfilesDep,
    clock: ClockDep,
) -> ActivationOut:
    name = await _check_references(storage, body.policy_id, body.excluded_tv_ids)
    now = await household_now(storage.settings, clock)
    local_until = (
        next_midnight(now) if body.minutes is None else now + timedelta(minutes=body.minutes)
    )
    activation = await profiles.activate(
        body.policy_id,
        local_until.astimezone(UTC),
        frozenset(body.excluded_tv_ids),
        body.source,
    )
    await _nudge_all(storage, supervisor)
    return _activation_out(activation, name)


@router.delete("/profiles/active", status_code=204, responses=AUTH_ERRORS)
async def stop(
    _: CanControl, storage: StorageDep, supervisor: SupervisorDep, profiles: ProfilesDep
) -> Response:
    await profiles.stop()
    await _nudge_all(storage, supervisor)
    return Response(status_code=204)


# --- calendar -------------------------------------------------------------------------------


def _to_domain(doc: WeeklyEntryDoc | DatedEntryDoc) -> CalendarEntry:
    excluded = frozenset(doc.excluded_tv_ids)
    if isinstance(doc, WeeklyEntryDoc):
        return WeeklyEntry(doc.policy_id, frozenset(doc.weekdays), doc.start, doc.end, excluded)
    return DatedEntry(doc.policy_id, doc.start_date, doc.end_date, excluded)


def _entry_out(entry_id: int, entry: CalendarEntry) -> WeeklyEntryOut | DatedEntryOut:
    excluded = sorted(entry.excluded_tv_ids)
    if isinstance(entry, WeeklyEntry):
        return WeeklyEntryOut(
            id=entry_id,
            kind="weekly",
            policy_id=entry.policy_id,
            weekdays=sorted(entry.weekdays),
            start=entry.start,
            end=entry.end,
            excluded_tv_ids=excluded,
        )
    return DatedEntryOut(
        id=entry_id,
        kind="dated",
        policy_id=entry.policy_id,
        start_date=entry.start_date,
        end_date=entry.end_date,
        excluded_tv_ids=excluded,
    )


@router.get("/calendar", response_model=CalendarOut, responses=AUTH_ERRORS)
async def list_entries(_: CanRead, storage: StorageDep, profiles: ProfilesDep) -> CalendarOut:
    records = await storage.profiles.entries()
    return CalendarOut(
        effective=profiles.effective,
        entries=[_entry_out(r.id, r.entry) for r in records],
    )


@router.post(
    "/calendar", response_model=CalendarEntryOut, status_code=201, responses=NOT_FOUND_ERRORS
)
async def add_entry(
    body: CalendarEntryDoc, _: CanAdmin, storage: StorageDep, supervisor: SupervisorDep
) -> WeeklyEntryOut | DatedEntryOut:
    await _check_references(storage, body.policy_id, body.excluded_tv_ids)
    entry = _to_domain(body)
    entry_id = await storage.profiles.add_entry(entry)
    await _nudge_all(storage, supervisor)
    return _entry_out(entry_id, entry)


@router.put("/calendar/{entry_id}", response_model=CalendarEntryOut, responses=NOT_FOUND_ERRORS)
async def replace_entry(
    entry_id: int,
    body: CalendarEntryDoc,
    _: CanAdmin,
    storage: StorageDep,
    supervisor: SupervisorDep,
) -> WeeklyEntryOut | DatedEntryOut:
    await _check_references(storage, body.policy_id, body.excluded_tv_ids)
    entry = _to_domain(body)
    if not await storage.profiles.update_entry(entry_id, entry):
        raise not_found("calendar entry")
    await _nudge_all(storage, supervisor)
    return _entry_out(entry_id, entry)


@router.delete("/calendar/{entry_id}", status_code=204, responses=NOT_FOUND_ERRORS)
async def delete_entry(
    entry_id: int, _: CanAdmin, storage: StorageDep, supervisor: SupervisorDep
) -> Response:
    if not await storage.profiles.delete_entry(entry_id):
        raise not_found("calendar entry")
    await _nudge_all(storage, supervisor)
    return Response(status_code=204)
