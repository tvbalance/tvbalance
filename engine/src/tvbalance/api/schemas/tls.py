"""HTTPS on the local network: status of the certificate and the local CA."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TlsStatusOut(BaseModel):
    mode: str
    active: bool
    https_port: int
    names: list[str]
    skipped_names: list[str]
    urls: list[str]
    expires_at: datetime | None
    ca_fingerprint: str | None
    error: str | None
