import pytest

from tvbalance.domain.models import Power
from tvbalance.sdk.types import AppInfo, ChannelInfo, InputInfo
from tvbalance_adapter_webos.mapping import (
    LIVETV_APP_ID,
    app_infos,
    channel_infos,
    input_infos,
    power_from_state,
    split_foreground,
)

INPUT_ROWS = [{"id": "HDMI_1", "label": "HDMI 1", "appId": "com.webos.app.hdmi1"}]


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("Active", Power.ON),
        ("Screen Saver", Power.ON),
        ("Screen Off", Power.STANDBY),
        ("Active Standby", Power.STANDBY),
        ("Suspend", Power.STANDBY),
        ("Power Off", Power.OFF),
        ("Something New", Power.ON),
    ],
)
def test_power_states(state: str, expected: Power) -> None:
    assert power_from_state(state) is expected


def test_missing_power_state_means_on() -> None:
    assert power_from_state(None) is Power.ON


def test_livetv_is_not_an_app() -> None:
    assert split_foreground(LIVETV_APP_ID, INPUT_ROWS) == (None, None, True)


def test_hdmi_app_becomes_an_input() -> None:
    assert split_foreground("com.webos.app.hdmi1", INPUT_ROWS) == (None, "HDMI_1", False)


def test_other_apps_pass_through() -> None:
    assert split_foreground("netflix", INPUT_ROWS) == ("netflix", None, False)


def test_empty_foreground_is_nothing() -> None:
    assert split_foreground(None, INPUT_ROWS) == (None, None, False)
    assert split_foreground("", INPUT_ROWS) == (None, None, False)


def test_unknown_hdmi_app_is_still_an_input_by_its_app_id() -> None:
    assert split_foreground("com.webos.app.hdmi7", []) == (None, "com.webos.app.hdmi7", False)


def test_apps_skip_non_dict_and_incomplete_rows() -> None:
    rows = [{"id": "kids", "title": "Kids", "icon": "http://x/i.png"}, "BOGUS", {"title": "No id"}]
    assert app_infos(rows) == [AppInfo("kids", "Kids", "http://x/i.png")]


def test_app_without_title_or_icon() -> None:
    assert app_infos([{"id": "a"}]) == [AppInfo("a", "a", None)]
    assert app_infos([{"id": "a", "title": "A", "icon": ""}]) == [AppInfo("a", "A", None)]


def test_inputs_skip_junk() -> None:
    assert input_infos([*INPUT_ROWS, "BOGUS", {"label": "x"}]) == [InputInfo("HDMI_1", "HDMI 1")]


def test_channels_skip_junk() -> None:
    rows = [{"channelId": "c1", "channelName": "One", "channelNumber": "1"}, "BOGUS", {}]
    assert channel_infos(rows) == [ChannelInfo("c1", "One", "1")]


def test_none_lists_are_empty() -> None:
    assert app_infos(None) == input_infos(None) == channel_infos(None) == []
