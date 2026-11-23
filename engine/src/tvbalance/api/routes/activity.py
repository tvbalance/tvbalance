"""Viewing time per day and the event history."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from tvbalance.api.deps import CanRead, get_clock, get_entitlements, get_storage
from tvbalance.api.errors import ApiError
from tvbalance.api.routes.tvs import existing_tv
from tvbalance.api.schemas.activity import (
    ContentUsageItem,
    ContentUsageOut,
    EventOut,
    UsageDayOut,
    UsageOut,
)
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.app.household import household_now
from tvbalance.ports.services import Clock, Entitlements
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1", tags=["activity"])

StorageDep = Annotated[Storage, Depends(get_storage)]
ClockDep = Annotated[Clock, Depends(get_clock)]
EntitlementsDep = Annotated[Entitlements, Depends(get_entitlements)]
DEFAULT_HISTORY = timedelta(days=7)
FREE_DAYS = 7  # how far back the Free plan sees; Pro sees up to MAX_DAYS
MAX_DAYS = 366


@router.get("/tvs/{tv_id}/usage", response_model=UsageOut, responses=NOT_FOUND_ERRORS)
async def usage(
    tv_id: str,
    _: CanRead,
    storage: StorageDep,
    clock: ClockDep,
    entitlements: EntitlementsDep,
    days: Annotated[int, Query(ge=1, le=MAX_DAYS)] = 7,
) -> UsageOut:
    """Viewing time per day. The Free plan sees the last seven days; ``limited`` says it was cut."""
    await existing_tv(storage, tv_id)
    limited = not entitlements.is_pro() and days > FREE_DAYS
    days = FREE_DAYS if limited else days
    today = (await household_now(storage.settings, clock)).date()
    rows = [await storage.usage.get(tv_id, today - timedelta(days=back)) for back in range(days)]
    return UsageOut(
        tv_id=tv_id,
        days=[
            UsageDayOut(day=u.day, watched_seconds=u.watched_seconds, bonus_minutes=u.bonus_minutes)
            for u in rows
        ],
        limited=limited,
    )


@router.get(
    "/tvs/{tv_id}/usage/content",
    response_model=ContentUsageOut,
    responses=NOT_FOUND_ERRORS,
)
async def content_usage(
    tv_id: str,
    _: CanRead,
    storage: StorageDep,
    clock: ClockDep,
    entitlements: EntitlementsDep,
    first: Annotated[date | None, Query(alias="from")] = None,
    last: Annotated[date | None, Query(alias="to")] = None,
) -> ContentUsageOut:
    """Seconds viewed per app, input and channel between two days, most viewed first.

    Without ``from``/``to`` the last seven days are summed. The Free plan cannot go further back
    than seven days: an earlier ``from`` is moved up and ``limited`` is set.
    """
    await existing_tv(storage, tv_id)
    today = (await household_now(storage.settings, clock)).date()
    last = min(last or today, today)
    first = first or last - timedelta(days=FREE_DAYS - 1)
    if first > last or (last - first).days >= MAX_DAYS:
        raise ApiError(422, "invalid_range", "the range must be at most a year, oldest day first")
    oldest_free = today - timedelta(days=FREE_DAYS - 1)
    limited = not entitlements.is_pro() and first < oldest_free
    if limited:
        first = oldest_free
        last = max(last, first)
    used = await storage.content_usage.between(tv_id, first, last)
    ranked = sorted(used.items(), key=lambda item: (-item[1], item[0].kind, item[0].id))
    return ContentUsageOut(
        tv_id=tv_id,
        first=first,
        last=last,
        items=[ContentUsageItem(kind=k.kind, id=k.id, seconds=s) for k, s in ranked],
        limited=limited,
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
