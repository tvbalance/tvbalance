"""The Pro license: what the plan allows, and the key that unlocks it."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LicenseOut(BaseModel):
    status: Literal["none", "active", "expired", "invalid"]
    tier: Literal["free", "pro"]
    licensee: str | None
    expires_at: datetime | None  # null: perpetual
    max_tvs: int | None  # null: unlimited
    checkout_url: str  # where to buy Pro; empty when none is configured


class LicenseKeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=4096)
