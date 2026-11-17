"""What a parent does in the moment: allow or block now, grant extra time, pause."""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from tvbalance.api.deps import CanControl, get_clock, get_storage, get_supervisor
from tvbalance.api.routes.tvs import existing_tv
from tvbalance.api.schemas.control import (
    BonusOut,
    BonusRequest,
    OverrideOut,
    OverrideRequest,
    PauseRequest,
)
from tvbalance.api.schemas.errors import NOT_FOUND_ERRORS
from tvbalance.app.household import household_now, next_midnight
from tvbalance.app.supervisor import Supervisor
from tvbalance.domain.models import Override
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1/tvs/{tv_id}", tags=["control"])

StorageDep = Annotated[Storage, Depends(get_storage)]
SupervisorDep = Annotated[Supervisor, Depends(get_supervisor)]


ClockDep = Annotated[Clock, Depends(get_clock)]


async def _override(
    tv_id: str,
    allow: bool,
    minutes: int | None,
    storage: Storage,
    supervisor: Supervisor,
    clock: Clock,
) -> OverrideOut:
    await existing_tv(storage, tv_id)
    now = await household_now(storage.settings, clock)
    local_until = next_midnight(now) if minutes is None else now + timedelta(minutes=minutes)
    until, now = local_until.astimezone(UTC), now.astimezone(UTC)
    override = Override(allow=allow, until=until, created_at=now)
    await storage.overrides.add(tv_id, override)
    supervisor.nudge(tv_id)
    return OverrideOut(allow=allow, until=until, created_at=now)


@router.post("/override", response_model=OverrideOut, responses=NOT_FOUND_ERRORS)
async def set_override(
    tv_id: str,
    body: OverrideRequest,
    _: CanControl,
    storage: StorageDep,
    supervisor: SupervisorDep,
    clock: ClockDep,
) -> OverrideOut:
    return await _override(tv_id, body.allow, body.minutes, storage, supervisor, clock)


@router.delete("/override", status_code=204, responses=NOT_FOUND_ERRORS)
async def clear_overrides(
    tv_id: str, _: CanControl, storage: StorageDep, supervisor: SupervisorDep
) -> Response:
    await existing_tv(storage, tv_id)
    await storage.overrides.clear(tv_id)
    supervisor.nudge(tv_id)
    return Response(status_code=204)


@router.post("/bonus", response_model=BonusOut, responses=NOT_FOUND_ERRORS)
async def grant_bonus(
    tv_id: str,
    body: BonusRequest,
    _: CanControl,
    storage: StorageDep,
    supervisor: SupervisorDep,
    clock: ClockDep,
) -> BonusOut:
    await existing_tv(storage, tv_id)
    today = (await household_now(storage.settings, clock)).date()
    await storage.usage.add_bonus(tv_id, today, body.minutes)
    supervisor.nudge(tv_id)
    return BonusOut(day=today, bonus_minutes=(await storage.usage.get(tv_id, today)).bonus_minutes)


@router.post("/pause", response_model=OverrideOut, responses=NOT_FOUND_ERRORS)
async def pause(
    tv_id: str,
    body: PauseRequest,
    _: CanControl,
    storage: StorageDep,
    supervisor: SupervisorDep,
    clock: ClockDep,
) -> OverrideOut:
    """An instant pause: block the TV for a while, whatever the schedule says."""
    return await _override(tv_id, False, body.minutes, storage, supervisor, clock)
