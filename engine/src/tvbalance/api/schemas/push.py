"""Web Push subscriptions of the devices that receive notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, cast
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import AfterValidator, BaseModel, Field

from tvbalance.app.notifications import PUSH_EVENTS
from tvbalance.infra.webpush import b64url_decode

PushEvent = Literal["pairing_lost", "tv_unreachable", "blocked", "time_warning"]
DEFAULT_EVENTS: frozenset[str] = PUSH_EVENTS


def _https(value: str) -> str:
    if urlsplit(value).scheme != "https" or not urlsplit(value).netloc:
        raise ValueError("must be an https URL")
    return value


def _web_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("must be an http(s) URL")
    return value


def _public_key(value: str) -> str:
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64url_decode(value))
    except ValueError as ex:
        raise ValueError("must be a base64url P-256 public key") from ex
    return value


def _auth_secret(value: str) -> str:
    try:
        raw = b64url_decode(value)
    except ValueError as ex:
        raise ValueError("must be base64url") from ex
    if len(raw) != 16:
        raise ValueError("must be 16 bytes")
    return value


class PushKeys(BaseModel):
    p256dh: Annotated[str, AfterValidator(_public_key)]
    auth: Annotated[str, AfterValidator(_auth_secret)]


class PushSubscriptionCreate(BaseModel):
    endpoint: Annotated[str, Field(max_length=2048), AfterValidator(_https)]
    keys: PushKeys
    events: list[PushEvent] = Field(
        default_factory=lambda: cast(list[PushEvent], sorted(DEFAULT_EVENTS))
    )
    language: Annotated[str, Field(max_length=16)] = "en"
    app_url: Annotated[str, Field(max_length=2048), AfterValidator(_web_url)]


class PushSubscriptionUpdate(BaseModel):
    events: list[PushEvent]


class PushSubscriptionOut(BaseModel):
    id: str
    events: list[PushEvent]
    language: str
    user_agent: str
    created_at: datetime
    last_sent_at: datetime | None
    current: bool = False


class PushKeyOut(BaseModel):
    public_key: str


class PushTestOut(BaseModel):
    result: Literal["delivered", "gone", "failed"]
