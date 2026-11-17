"""Parent controls: temporary overrides, extra minutes and instant pauses."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_OVERRIDE_MINUTES = 24 * 60


class OverrideRequest(BaseModel):
    """Allow or block a TV for a while: give ``minutes`` or ask for ``until_midnight``."""

    model_config = ConfigDict(extra="forbid")

    allow: bool
    minutes: int | None = Field(default=None, ge=1, le=MAX_OVERRIDE_MINUTES)
    until_midnight: bool = False

    @model_validator(mode="after")
    def _one_duration(self) -> OverrideRequest:
        if (self.minutes is None) == (not self.until_midnight):
            raise ValueError("give either minutes or until_midnight")
        return self


class OverrideOut(BaseModel):
    allow: bool
    until: datetime
    created_at: datetime


class BonusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minutes: int = Field(ge=1, le=240)


class BonusOut(BaseModel):
    day: date
    bonus_minutes: int  # all the bonus granted today, this request included


class PauseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minutes: int = Field(default=30, ge=1, le=MAX_OVERRIDE_MINUTES)
