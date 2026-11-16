from tvbalance.domain.models import MessageKind, ShowMessage
from tvbalance.sdk.messages import default_text


def test_explicit_text_wins() -> None:
    assert default_text(ShowMessage(MessageKind.TIME_UP, text="Basta!")) == "Basta!"


def test_every_kind_has_a_default() -> None:
    for kind in MessageKind:
        assert default_text(ShowMessage(kind))


def test_warning_mentions_minutes() -> None:
    assert "5" in default_text(ShowMessage(MessageKind.TIME_WARNING, 5))
