"""EnforcementState <-> versioned JSON document. Change the stored form by versioning it."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from tvbalance.domain.enforcement import EnforcementState

VERSION = 1


class StateDecodeError(ValueError):
    """The stored document is not an enforcement state this version understands."""


def encode_state(state: EnforcementState) -> dict[str, Any]:
    return {
        "version": VERSION,
        "day": None if state.day is None else state.day.isoformat(),
        "warned": sorted(state.warned),
        "episode_started": _encode_moment(state.episode_started),
        "acted_at": _encode_moment(state.acted_at),
        "last_message_at": _encode_moment(state.last_message_at),
        "redirected": state.redirected,
        "unavailable_reported": state.unavailable_reported,
        "power_offs": [moment.isoformat() for moment in state.power_offs],
        "paused_until": _encode_moment(state.paused_until),
    }


def decode_state(doc: Any) -> EnforcementState:
    if not isinstance(doc, dict) or doc.get("version") != VERSION:
        version = doc.get("version") if isinstance(doc, dict) else None
        raise StateDecodeError(f"unsupported enforcement state (version {version!r})")
    try:
        return EnforcementState(
            day=None if doc["day"] is None else date.fromisoformat(doc["day"]),
            warned=frozenset(_ints(doc["warned"])),
            episode_started=_decode_moment(doc["episode_started"]),
            acted_at=_decode_moment(doc["acted_at"]),
            last_message_at=_decode_moment(doc["last_message_at"]),
            redirected=_flag(doc["redirected"]),
            unavailable_reported=_flag(doc["unavailable_reported"]),
            power_offs=tuple(_moments(doc["power_offs"])),
            paused_until=_decode_moment(doc["paused_until"]),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as ex:
        raise StateDecodeError(f"malformed enforcement state: {ex!r}") from ex


def _encode_moment(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()


def _decode_moment(value: Any) -> datetime | None:
    if value is None:
        return None
    moment = datetime.fromisoformat(value)  # TypeError unless a string
    if moment.tzinfo is None:
        raise ValueError("moments must carry a UTC offset")
    return moment


def _moments(values: Any) -> list[datetime]:
    if not isinstance(values, list):
        raise TypeError("expected a list of moments")
    moments = [_decode_moment(value) for value in values]
    return [moment for moment in moments if moment is not None]


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in values
    ):
        raise TypeError("expected a list of integers")
    return values


def _flag(value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError("expected a boolean")
    return value
