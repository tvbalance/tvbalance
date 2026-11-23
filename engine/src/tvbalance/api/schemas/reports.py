"""The weekly report."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ReportDayOut(BaseModel):
    day: date
    seconds: int


class ReportContentOut(BaseModel):
    kind: str  # "app", "input" or "channel"
    id: str
    seconds: int


class TvReportOut(BaseModel):
    tv_id: str
    tv_name: str
    total_seconds: int
    days: list[ReportDayOut]  # oldest first, seven of them
    top_content: list[ReportContentOut]  # most viewed first
    blocks: int  # how many times content was blocked


class WeeklyReportOut(BaseModel):
    first: date  # a Monday
    last: date  # the Sunday after it
    tvs: list[TvReportOut]
