"""System schemas: liveness, version and the adapters the engine can drive."""

from __future__ import annotations

from pydantic import BaseModel

from tvbalance.sdk.types import Capability, Maturity


class HealthResponse(BaseModel):
    status: str


class AdapterOut(BaseModel):
    id: str
    brand: str
    display_name: str
    maturity: Maturity
    capabilities: list[Capability]


class InfoResponse(BaseModel):
    version: str
    api_version: str
