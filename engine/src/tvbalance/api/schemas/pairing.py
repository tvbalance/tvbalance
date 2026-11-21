"""Discovery and pairing schemas."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    """What to pair: a new TV (its adapter and host) or, with ``tv_id``, a stored TV again."""

    model_config = ConfigDict(extra="forbid")

    adapter_id: str | None = Field(default=None, min_length=1, max_length=64)
    host: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    tv_id: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _new_or_again(self) -> PairingStart:
        if self.tv_id is not None:
            if self.host is not None:
                raise ValueError("a stored TV keeps its address: leave host out")
        elif self.adapter_id is None or self.host is None:
            raise ValueError("adapter_id and host are needed to add a TV")
        return self

    @field_validator("host")
    @classmethod
    def _bare_host(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
