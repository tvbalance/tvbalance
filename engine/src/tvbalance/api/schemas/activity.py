"""What happened: viewing time per day and the event history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class UsageDayOut(BaseModel):
    day: date
    watched_seconds: int
    bonus_minutes: int


class UsageOut(BaseModel):
    tv_id: str
    days: list[UsageDayOut]  # newest first, today included


class EventOut(BaseModel):
    id: int
    tv_id: str | None
    occurred_at: datetime
    type: str
    payload: dict[str, Any]
