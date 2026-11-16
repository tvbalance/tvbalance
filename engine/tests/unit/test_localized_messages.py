import re

import pytest

from tvbalance.app.messages import LANGUAGES, localize, messages_for
from tvbalance.domain.models import GoHome, MessageKind, ShowMessage

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_every_locale_has_the_same_keys_and_placeholders() -> None:
    english = messages_for("en")
    for language in LANGUAGES:
        texts = messages_for(language)
        assert texts.keys() == english.keys(), language
        for key, text in texts.items():
            assert PLACEHOLDER.findall(text) == PLACEHOLDER.findall(english[key]), (language, key)


def test_every_message_kind_has_a_text() -> None:
    assert {kind.value for kind in MessageKind} <= messages_for("en").keys()


@pytest.mark.parametrize("language", LANGUAGES)
def test_texts_are_filled_in_every_language(language: str) -> None:
    for message in (
        ShowMessage(MessageKind.TIME_WARNING, 5),
        ShowMessage(MessageKind.TIME_WARNING, 1),
        ShowMessage(MessageKind.TIME_WARNING),
        ShowMessage(MessageKind.TIME_UP),
        ShowMessage(MessageKind.CONTENT_BLOCKED),
        ShowMessage(MessageKind.POWERING_OFF),
    ):
        action = localize(message, language)
        assert isinstance(action, ShowMessage)
        assert action.text
        assert "{" not in action.text


def test_minutes_are_inserted() -> None:
    action = localize(ShowMessage(MessageKind.TIME_WARNING, 5), "it")
    assert isinstance(action, ShowMessage)
    assert action.text is not None
    assert "5" in action.text
    assert action.minutes_left == 5


def test_one_minute_uses_the_singular() -> None:
    one = localize(ShowMessage(MessageKind.TIME_WARNING, 1), "en")
    assert isinstance(one, ShowMessage)
    assert one.text == "TV time ends in 1 minute."


@pytest.mark.parametrize("language", ["it-IT", "IT", "it_IT"])
def test_language_tags_are_normalized(language: str) -> None:
    assert localize(ShowMessage(MessageKind.TIME_UP), language) == localize(
        ShowMessage(MessageKind.TIME_UP), "it"
    )


@pytest.mark.parametrize("language", ["xx", "", "zh-CN"])
def test_unknown_language_falls_back_to_english(language: str) -> None:
    action = localize(ShowMessage(MessageKind.TIME_UP), language)
    assert isinstance(action, ShowMessage)
    assert action.text == "TV time is over."


def test_existing_text_is_kept() -> None:
    message = ShowMessage(MessageKind.TIME_UP, text="Custom")
    assert localize(message, "it") == message


def test_other_actions_are_untouched() -> None:
    assert localize(GoHome(), "it") == GoHome()
