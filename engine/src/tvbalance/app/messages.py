"""Localized on-screen texts. The domain names a message; this module gives it words."""

from __future__ import annotations

import json
from dataclasses import replace
from functools import cache
from importlib.resources import files

from tvbalance.domain.models import Action, MessageKind, ShowMessage

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "it", "de", "fr", "es")


@cache
def messages_for(language: str) -> dict[str, str]:
    """The texts of one of ``LANGUAGES``, keyed by message kind."""
    resource = files("tvbalance").joinpath("locales", f"{language}.json")
    texts: dict[str, str] = json.loads(resource.read_text(encoding="utf-8"))
    return texts


def _supported(language: str) -> str:
    primary = language.replace("_", "-").split("-")[0].lower()
    return primary if primary in LANGUAGES else DEFAULT_LANGUAGE


def _key(message: ShowMessage) -> str:
    if message.kind is not MessageKind.TIME_WARNING:
        return message.kind.value
    if not message.minutes_left:
        return "time_warning_soon"
    return "time_warning_one" if message.minutes_left == 1 else "time_warning"


def localize(action: Action, language: str) -> Action:
    """``action`` with the on-screen text filled in; other actions pass through unchanged."""
    if not isinstance(action, ShowMessage) or action.text:
        return action
    text = messages_for(_supported(language))[_key(action)]
    return replace(action, text=text.format(minutes=action.minutes_left))
