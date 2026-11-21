"""What a TV offers that a rule can name."""

from __future__ import annotations

from pydantic import BaseModel


class AppOut(BaseModel):
    id: str
    name: str
    has_icon: (
        bool  # fetch it from the icon endpoint: the TV's own address is not reachable by browsers
    )


class InputOut(BaseModel):
    id: str
    label: str


class ChannelOut(BaseModel):
    id: str
    name: str
    number: str | None


class InventoryOut(BaseModel):
    apps: list[AppOut]
    inputs: list[InputOut]
    channels: list[ChannelOut]
