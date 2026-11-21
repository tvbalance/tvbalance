"""Discovery and pairing schemas."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HOSTNAME = re.compile(
    r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


class FoundTvOut(BaseModel):
    adapter_id: str
    adapter_name: str
    host: str
    name: str
    model: str | None
    already_added: bool


class PairingStart(BaseModel):
    """What to pair: the adapter (brand) and the TV's host name or IP address, nothing else."""

    model_config = ConfigDict(extra="forbid")

    adapter_id: str = Field(min_length=1, max_length=64)
    host: str
    name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("host")
    @classmethod
    def _bare_host(cls, value: str) -> str:
        host = value.strip()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if len(host) > 253 or not _HOSTNAME.match(host):
                raise ValueError(
                    "enter a host name or an IP address, without scheme, port or path"
                ) from None
        return host


class PairingOut(BaseModel):
    id: str
    state: Literal["waiting_for_user", "completed", "failed", "expired"]
    adapter_id: str
    host: str
    tv_id: str | None  # set once the TV is stored
    expires_at: datetime
