"""Authentication schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Scope = Literal["read", "control", "admin"]


class Request(BaseModel):
    """Bodies refuse unknown fields, so a typo is an error rather than a silent no-op."""

    model_config = ConfigDict(extra="forbid")


class AuthState(BaseModel):
    setup_required: bool


class SetupRequest(Request):
    password: str = Field(max_length=1024)


class LoginRequest(Request):
    password: str = Field(max_length=1024)


class PinLoginRequest(Request):
    pin: str = Field(max_length=64)


class PasswordChange(Request):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(max_length=1024)


class PinSet(Request):
    pin: str = Field(max_length=64)


class Me(BaseModel):
    kind: Literal["admin", "pin", "token", "ingress"]
    name: str
    scopes: list[Scope]
    full_admin: bool
    session_id: str | None
    csrf_token: str | None  # echo it in X-TVBalance-CSRF on cookie-authenticated writes


class SessionOut(BaseModel):
    id: str
    kind: Literal["admin", "pin"]
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    user_agent: str
    current: bool


class TokenCreate(Request):
    name: str = Field(max_length=100)
    scopes: list[Scope]


class TokenOut(BaseModel):
    id: str
    name: str
    scopes: list[Scope]
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class TokenCreated(TokenOut):
    token: str  # shown once: only its hash is kept


class Revoked(BaseModel):
    revoked: int
