"""Policy <-> versioned JSON document. The stored form is a contract: change it by versioning."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, time, timedelta
from typing import Any

from tvbalance.domain.models import (
    AppTarget,
    ChannelTarget,
    EscalationSettings,
    HomeTarget,
    InputTarget,
    Policy,
    Schedule,
    Target,
    TimeWindow,
)

VERSION = 1


class PolicyDecodeError(ValueError):
    """The stored document is not a policy this version understands."""


def encode_policy(policy: Policy) -> dict[str, Any]:
    return {
        "version": VERSION,
        "schedule": {
            "windows": {
                str(day): _encode_windows(windows)
                for day, windows in sorted(policy.schedule.windows.items())
            },
            "special_days": {
                day.isoformat(): _encode_windows(windows)
                for day, windows in sorted(policy.schedule.special_days.items())
            },
        },
        "daily_budget_minutes": policy.daily_budget_minutes,
        "blocked_apps": sorted(policy.blocked_apps),
        "blocked_inputs": sorted(policy.blocked_inputs),
        "blocked_channels": sorted(policy.blocked_channels),
        "allow_list_apps": None
        if policy.allow_list_apps is None
        else sorted(policy.allow_list_apps),
        "always_allowed_apps": sorted(policy.always_allowed_apps),
        "always_allowed_inputs": sorted(policy.always_allowed_inputs),
        "always_allowed_channels": sorted(policy.always_allowed_channels),
        "fallback": None if policy.fallback is None else _encode_target(policy.fallback),
        "warn_at_minutes": list(policy.warn_at_minutes),
        "escalation": _encode_escalation(policy.escalation),
    }


def decode_policy(doc: Any) -> Policy:
    if not isinstance(doc, dict) or doc.get("version") != VERSION:
        version = doc.get("version") if isinstance(doc, dict) else None
        raise PolicyDecodeError(f"unsupported policy document (version {version!r})")
    try:
        return Policy(
            schedule=Schedule(
                windows={
                    int(day): _decode_windows(windows)
                    for day, windows in doc["schedule"]["windows"].items()
                },
                special_days={
                    date.fromisoformat(day): _decode_windows(windows)
                    for day, windows in doc["schedule"]["special_days"].items()
                },
            ),
            daily_budget_minutes=doc["daily_budget_minutes"],
            blocked_apps=_strings(doc["blocked_apps"]),
            blocked_inputs=_strings(doc["blocked_inputs"]),
            blocked_channels=_strings(doc["blocked_channels"]),
            allow_list_apps=None
            if doc["allow_list_apps"] is None
            else _strings(doc["allow_list_apps"]),
            always_allowed_apps=_strings(doc["always_allowed_apps"]),
            always_allowed_inputs=_strings(doc["always_allowed_inputs"]),
            always_allowed_channels=_strings(doc["always_allowed_channels"]),
            fallback=None if doc["fallback"] is None else _decode_target(doc["fallback"]),
            warn_at_minutes=tuple(_ints(doc["warn_at_minutes"])),
            escalation=_decode_escalation(doc["escalation"]),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as ex:
        raise PolicyDecodeError(f"malformed policy document: {ex!r}") from ex


def _encode_windows(windows: Iterable[TimeWindow]) -> list[dict[str, str]]:
    return [{"start": w.start.isoformat(), "end": w.end.isoformat()} for w in windows]


def _decode_windows(rows: list[dict[str, str]]) -> tuple[TimeWindow, ...]:
    return tuple(
        TimeWindow(time.fromisoformat(r["start"]), time.fromisoformat(r["end"])) for r in rows
    )


def _strings(values: Any) -> frozenset[str]:
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise TypeError("expected a list of strings")
    return frozenset(values)


def _ints(values: Any) -> list[int]:
    if not isinstance(values, list) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in values
    ):
        raise TypeError("expected a list of integers")
    return values


_TARGET_KINDS: dict[str, Callable[[str], Target]] = {
    "app": AppTarget,
    "input": InputTarget,
    "channel": ChannelTarget,
}


def _encode_target(target: Target) -> dict[str, str]:
    match target:
        case AppTarget(app_id):
            return {"kind": "app", "id": app_id}
        case InputTarget(input_id):
            return {"kind": "input", "id": input_id}
        case ChannelTarget(channel_id):
            return {"kind": "channel", "id": channel_id}
        case HomeTarget():
            return {"kind": "home"}


def _decode_target(doc: dict[str, str]) -> Target:
    if doc["kind"] == "home":
        return HomeTarget()
    return _TARGET_KINDS[doc["kind"]](doc["id"])


def _encode_escalation(e: EscalationSettings) -> dict[str, float | int]:
    return {
        "debounce": e.debounce.total_seconds(),
        "grace": e.grace.total_seconds(),
        "power_off_cap": e.power_off_cap,
        "cap_window": e.cap_window.total_seconds(),
        "cap_pause": e.cap_pause.total_seconds(),
        "message_repeat": e.message_repeat.total_seconds(),
    }


def _decode_escalation(doc: dict[str, float | int]) -> EscalationSettings:
    return EscalationSettings(
        debounce=timedelta(seconds=doc["debounce"]),
        grace=timedelta(seconds=doc["grace"]),
        power_off_cap=int(doc["power_off_cap"]),
        cap_window=timedelta(seconds=doc["cap_window"]),
        cap_pause=timedelta(seconds=doc["cap_pause"]),
        message_repeat=timedelta(seconds=doc["message_repeat"]),
    )
