"""Viewing time per day and the event history."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from tvbalance.api.deps import CanRead, get_clock, get_storage
from tvbalance.api.routes.tvs import existing_tv
from tvbalance.api.schemas.activity import EventOut, UsageDayOut, UsageOut
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.app.household import household_now
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1", tags=["activity"])

StorageDep = Annotated[Storage, Depends(get_storage)]
ClockDep = Annotated[Clock, Depends(get_clock)]
DEFAULT_HISTORY = timedelta(days=7)


@router.get("/tvs/{tv_id}/usage", response_model=UsageOut, responses=NOT_FOUND_ERRORS)
async def usage(
    tv_id: str,
    _: CanRead,
    storage: StorageDep,
    clock: ClockDep,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> UsageOut:
    await existing_tv(storage, tv_id)
    today = (await household_now(storage.settings, clock)).date()
    rows = [await storage.usage.get(tv_id, today - timedelta(days=back)) for back in range(days)]
    return UsageOut(
        tv_id=tv_id,
        days=[
            UsageDayOut(day=u.day, watched_seconds=u.watched_seconds, bonus_minutes=u.bonus_minutes)
            for u in rows
        ],
    )


@router.get("/events", response_model=list[EventOut], responses=AUTH_ERRORS)
async def events(
    _: CanRead,
    storage: StorageDep,
    clock: ClockDep,
    tv_id: str | None = None,
    since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[EventOut]:
    """Newest first. Without ``since`` the last seven days are searched."""
    start = since or clock.now() - DEFAULT_HISTORY
    found = await storage.events.recent(tv_id, start, limit)
    return [
        EventOut(id=e.id, tv_id=e.tv_id, occurred_at=e.occurred_at, type=e.type, payload=e.payload)
        for e in found
    ]
