"""English fallback texts for on-screen messages, used when the supervisor supplies none."""

from __future__ import annotations

from tvbalance.domain.models import MessageKind, ShowMessage


def default_text(message: ShowMessage) -> str:
    """The text an adapter shows for ``message``: its own ``text`` or an English default."""
    if message.text:
        return message.text
    minutes = message.minutes_left
    match message.kind:
        case MessageKind.TIME_WARNING:
            return f"TV time ends in {minutes} minutes." if minutes else "TV time is ending soon."
        case MessageKind.TIME_UP:
            return "TV time is over."
        case MessageKind.CONTENT_BLOCKED:
            return "This content is not available right now."
        case MessageKind.POWERING_OFF:
            return "The TV is turning off."
