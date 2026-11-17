"""Engine-wide settings."""

from __future__ import annotations

from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_validator

Language = Literal["en", "it", "de", "fr", "es"]


class SettingsOut(BaseModel):
    language: Language
    timezone: str | None  # an IANA name; null follows the system zone


class SettingsUpdate(BaseModel):
    """Only the fields present are changed; ``timezone: null`` goes back to the system zone."""

    model_config = ConfigDict(extra="forbid")

    language: Language | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, name: str | None) -> str | None:
        if name is not None:
            try:
                ZoneInfo(name)
            except (KeyError, ValueError, OSError) as ex:
                raise ValueError(f"unknown time zone {name!r}") from ex
        return name
