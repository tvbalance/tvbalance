"""Discovery and pairing schemas."""

from __future__ import annotations

from pydantic import BaseModel


class FoundTvOut(BaseModel):
    adapter_id: str
    adapter_name: str
    host: str
    name: str
    model: str | None
    already_added: bool
