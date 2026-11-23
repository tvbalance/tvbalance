"""The weekly report of how much each TV was watched. Pro only."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from tvbalance.api.deps import CanRead, get_clock, get_reports, get_storage
from tvbalance.api.errors import ApiError
from tvbalance.api.schemas.errors import AUTH_ERRORS
from tvbalance.api.schemas.reports import (
    ReportContentOut,
    ReportDayOut,
    TvReportOut,
    WeeklyReportOut,
)
from tvbalance.app.household import household_now
from tvbalance.app.reports import ReportService, previous_week
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1", tags=["reports"])

ReportsDep = Annotated[ReportService, Depends(get_reports)]
StorageDep = Annotated[Storage, Depends(get_storage)]
ClockDep = Annotated[Clock, Depends(get_clock)]


@router.get("/reports/weekly", response_model=WeeklyReportOut, responses=AUTH_ERRORS)
async def weekly_report(
    _: CanRead,
    reports: ReportsDep,
    storage: StorageDep,
    clock: ClockDep,
    week: date | None = None,
) -> WeeklyReportOut:
    """The week containing ``week`` (Monday to Sunday); the last complete week by default."""
    if not reports.effective:
        raise ApiError(403, "requires_pro", "the weekly report needs the Pro plan")
    today = (await household_now(storage.settings, clock)).date()
    report = await reports.build(week or previous_week(today))
    return WeeklyReportOut(
        first=report.first,
        last=report.last,
        tvs=[
            TvReportOut(
                tv_id=tv.tv_id,
                tv_name=tv.tv_name,
                total_seconds=tv.total_seconds,
                days=[ReportDayOut(day=d.day, seconds=d.seconds) for d in tv.days],
                top_content=[
                    ReportContentOut(kind=c.kind, id=c.id, seconds=c.seconds)
                    for c in tv.top_content
                ],
                blocks=tv.blocks,
            )
            for tv in report.tvs
        ],
    )
