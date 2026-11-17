"""Policy documents as the API speaks them: the stored form without its version number."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WindowDoc(Strict):
    start: time
    end: time


class ScheduleDoc(Strict):
    windows: dict[Annotated[int, Field(ge=0, le=6)], list[WindowDoc]] = {}
    special_days: dict[date, list[WindowDoc]] = {}


class TargetDoc(Strict):
    kind: Literal["app", "input", "channel", "home"]
    id: str | None = None

    @model_validator(mode="after")
    def _needs_an_id(self) -> TargetDoc:
        if (self.kind == "home") == (self.id is not None):
            raise ValueError(
                "only the home target goes without an id"
                if self.id is None
                else "the home target has no id"
            )
        return self


class EscalationDoc(Strict):
    debounce: float = Field(default=3, ge=0)
    grace: float = Field(default=15, ge=0)
    power_off_cap: int = Field(default=3, ge=1)
    cap_window: float = Field(default=300, ge=0)
    cap_pause: float = Field(default=600, ge=0)
    message_repeat: float = Field(default=60, ge=0)


class PolicyDoc(Strict):
    schedule: ScheduleDoc = ScheduleDoc()
    daily_budget_minutes: int | None = None
    blocked_apps: list[str] = []
    blocked_inputs: list[str] = []
    blocked_channels: list[str] = []
    allow_list_apps: list[str] | None = None
    always_allowed_apps: list[str] = []
    always_allowed_inputs: list[str] = []
    always_allowed_channels: list[str] = []
    fallback: TargetDoc | None = None
    warn_at_minutes: list[int] = [10, 5]
    escalation: EscalationDoc = EscalationDoc()


class PolicyCreate(Strict):
    name: str = Field(min_length=1, max_length=80)
    policy: PolicyDoc = PolicyDoc()


class PolicyUpdate(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    policy: PolicyDoc


class PolicyOut(BaseModel):
    id: int
    name: str
    policy: PolicyDoc
    updated_at: datetime
    tv_ids: list[str]
