"""TVs and their live status."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tvbalance.domain.models import Power


class DecisionOut(BaseModel):
    kind: Literal["allow", "warn", "block"]
    reason: str | None = None  # why a block happened (a BlockReason)
    limit: str | None = None  # what a warning is about (a LimitKind)
    minutes_left: int | None = None


class TvStatusOut(BaseModel):
    connected: bool
    pairing_required: bool
    power: Power | None
    foreground_app: str | None
    input_id: str | None
    channel_id: str | None
    program_title: str | None
    decision: DecisionOut | None
    watched_seconds: int
    remaining_seconds: int | None
    updated_at: datetime | None


class TvOut(BaseModel):
    id: str
    adapter_id: str
    name: str
    host: str
    policy_id: int | None
    enabled: bool
    needs_pairing: bool
    created_at: datetime
    status: TvStatusOut | None  # null while no worker runs (disabled or adapter missing)


class TvUpdate(BaseModel):
    """Only the fields present are changed; ``policy_id: null`` detaches the policy."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    enabled: bool | None = None
    policy_id: int | None = None
