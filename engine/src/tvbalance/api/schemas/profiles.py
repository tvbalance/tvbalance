"""Profiles and the calendar that switches them on."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tvbalance.api.schemas.control import MAX_OVERRIDE_MINUTES
from tvbalance.domain.profiles import ProfileSource


class ActivateRequest(BaseModel):
    """Put a rule set in force for the household: give ``minutes`` or ask for ``until_midnight``."""

    model_config = ConfigDict(extra="forbid")

    policy_id: int
    minutes: int | None = Field(default=None, ge=1, le=MAX_OVERRIDE_MINUTES)
    until_midnight: bool = False
    excluded_tv_ids: list[str] = Field(default_factory=list)  # these TVs keep their own rules
    source: Literal[ProfileSource.MANUAL, ProfileSource.AUTOMATION] = ProfileSource.MANUAL

    @model_validator(mode="after")
    def _one_duration(self) -> ActivateRequest:
        if (self.minutes is None) == (not self.until_midnight):
            raise ValueError("give either minutes or until_midnight")
        return self


class ActivationOut(BaseModel):
    policy_id: int
    name: str
    starts_at: datetime
    ends_at: datetime
    excluded_tv_ids: list[str]
    source: ProfileSource


class ActiveProfileOut(BaseModel):
    effective: bool  # false on the Free plan: the profile is stored but not applied
    activation: ActivationOut | None


class ProfileInfoOut(BaseModel):
    """The profile in force for one TV (from an activation or the calendar)."""

    policy_id: int
    name: str
    until: datetime
    source: ProfileSource


class _EntryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: int
    excluded_tv_ids: list[str] = Field(default_factory=list)


class WeeklyEntryDoc(_EntryBase):
    """Every listed weekday (0 = Monday); ``start > end`` crosses midnight, equal means 24 hours."""

    kind: Literal["weekly"]
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start: time
    end: time

    @model_validator(mode="after")
    def _weekdays(self) -> WeeklyEntryDoc:
        if len(set(self.weekdays)) != len(self.weekdays) or any(
            not 0 <= day <= 6 for day in self.weekdays
        ):
            raise ValueError("weekdays are distinct numbers from 0 (Monday) to 6 (Sunday)")
        return self


class DatedEntryDoc(_EntryBase):
    """Whole days from ``start_date`` to ``end_date``, both included (a holiday)."""

    kind: Literal["dated"]
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _order(self) -> DatedEntryDoc:
        if self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        return self


CalendarEntryDoc = Annotated[WeeklyEntryDoc | DatedEntryDoc, Field(discriminator="kind")]


class WeeklyEntryOut(WeeklyEntryDoc):
    id: int


class DatedEntryOut(DatedEntryDoc):
    id: int


CalendarEntryOut = Annotated[WeeklyEntryOut | DatedEntryOut, Field(discriminator="kind")]


class CalendarOut(BaseModel):
    effective: bool  # false on the Free plan: entries are stored but not applied
    entries: list[CalendarEntryOut]
