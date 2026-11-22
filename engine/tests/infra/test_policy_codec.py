import json
from copy import deepcopy
from datetime import date, time, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tvbalance.domain.models import (
    AppBudget,
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
from tvbalance.infra.db.policy_codec import PolicyDecodeError, decode_policy, encode_policy

FULL = Policy(
    schedule=Schedule(
        windows={
            0: (TimeWindow(time(16), time(20)),),
            4: (TimeWindow(time(16), time(23, 30)), TimeWindow(time(22), time(1))),
            6: (TimeWindow(time(0), time(0)),),
        },
        special_days={
            date(2026, 12, 25): (TimeWindow(time(9), time(21)),),
            date(2026, 12, 31): (),
        },
    ),
    daily_budget_minutes=90,
    blocked_apps=frozenset({"tiktok", "youtube"}),
    blocked_inputs=frozenset({"HDMI_2"}),
    blocked_channels=frozenset({"ch-7"}),
    allow_list_apps=frozenset({"netflix"}),
    always_allowed_apps=frozenset({"news"}),
    always_allowed_inputs=frozenset({"HDMI_1"}),
    always_allowed_channels=frozenset({"ch-1", "ch-2"}),
    fallback=ChannelTarget("ch-1"),
    warn_at_minutes=(15, 5, 1),
    escalation=EscalationSettings(
        debounce=timedelta(seconds=5),
        grace=timedelta(seconds=30),
        power_off_cap=2,
        cap_window=timedelta(minutes=10),
        cap_pause=timedelta(minutes=20),
        message_repeat=timedelta(seconds=90),
    ),
    weekday_budget_minutes={0: 60, 5: 180},
    app_budgets=(AppBudget("games", frozenset({"fortnite", "roblox"}), 45),),
    rollover_max_minutes=30,
)


def test_default_policy_round_trips() -> None:
    assert decode_policy(encode_policy(Policy())) == Policy()


def test_full_policy_round_trips() -> None:
    assert decode_policy(encode_policy(FULL)) == FULL


def test_the_document_is_plain_json_and_versioned() -> None:
    doc = encode_policy(FULL)
    assert doc["version"] == 2
    assert json.loads(json.dumps(doc)) == doc


def test_a_version_1_document_reads_without_advanced_budgets() -> None:
    doc = encode_policy(FULL)
    doc["version"] = 1
    for key in ("weekday_budget_minutes", "app_budgets", "rollover_max_minutes"):
        del doc[key]
    policy = decode_policy(doc)
    assert policy.weekday_budget_minutes == {}
    assert policy.app_budgets == ()
    assert policy.rollover_max_minutes is None
    assert policy.daily_budget_minutes == FULL.daily_budget_minutes


def test_equal_policies_give_identical_documents() -> None:
    other = Policy(blocked_apps=frozenset({"b", "a"}))
    same = Policy(blocked_apps=frozenset({"a", "b"}))
    assert json.dumps(encode_policy(other)) == json.dumps(encode_policy(same))
    assert encode_policy(same)["blocked_apps"] == ["a", "b"]


@pytest.mark.parametrize(
    "target", [AppTarget("netflix"), InputTarget("HDMI_1"), ChannelTarget("c1"), HomeTarget()]
)
def test_every_fallback_target_round_trips(target: Target) -> None:
    policy = Policy(fallback=target)
    assert decode_policy(encode_policy(policy)).fallback == target


def _broken(**changes: Any) -> Any:
    doc = deepcopy(encode_policy(FULL))
    doc.update(changes)
    return doc


@pytest.mark.parametrize(
    "doc",
    [
        None,
        [],
        "policy",
        {},
        {"version": 3},
        {"version": "1"},
        _broken(version=0),
        _broken(fallback={"kind": "moon"}),
        _broken(fallback={"kind": "app"}),
        _broken(schedule={"windows": {"monday": []}, "special_days": {}}),
        _broken(
            schedule={"windows": {"0": [{"start": "25:00", "end": "26:00"}]}, "special_days": {}}
        ),
        _broken(schedule={"windows": {}, "special_days": {"someday": []}}),
        _broken(escalation={"debounce": "fast"}),
        _broken(blocked_apps="tiktok"),
        _broken(warn_at_minutes=None),
        _broken(weekday_budget_minutes={"monday": 60}),
        _broken(app_budgets=[{"name": "g", "apps": "a", "minutes": 5}]),
        _broken(rollover_max_minutes="lots"),
    ],
)
def test_bad_documents_are_rejected(doc: Any) -> None:
    with pytest.raises(PolicyDecodeError):
        decode_policy(doc)


def test_a_missing_field_is_rejected() -> None:
    doc = encode_policy(FULL)
    del doc["escalation"]
    with pytest.raises(PolicyDecodeError):
        decode_policy(doc)


times = st.builds(time, st.integers(0, 23), st.integers(0, 59), st.integers(0, 59))
window_tuples = st.lists(st.builds(TimeWindow, times, times), max_size=3).map(tuple)
ids = st.text(min_size=1, max_size=8)
id_sets = st.frozensets(ids, max_size=4)
seconds = st.integers(0, 7200).map(lambda s: timedelta(seconds=s))
targets = st.one_of(
    st.builds(AppTarget, ids),
    st.builds(InputTarget, ids),
    st.builds(ChannelTarget, ids),
    st.just(HomeTarget()),
)
policies = st.builds(
    Policy,
    schedule=st.builds(
        Schedule,
        windows=st.dictionaries(st.integers(0, 6), window_tuples, max_size=7),
        special_days=st.dictionaries(
            st.dates(min_value=date(2026, 1, 1), max_value=date(2030, 12, 31)),
            window_tuples,
            max_size=4,
        ),
    ),
    daily_budget_minutes=st.none() | st.integers(0, 1440),
    blocked_apps=id_sets,
    blocked_inputs=id_sets,
    blocked_channels=id_sets,
    allow_list_apps=st.none() | id_sets,
    always_allowed_apps=id_sets,
    always_allowed_inputs=id_sets,
    always_allowed_channels=id_sets,
    fallback=st.none() | targets,
    warn_at_minutes=st.lists(st.integers(1, 60), max_size=4).map(tuple),
    escalation=st.builds(
        EscalationSettings,
        debounce=seconds,
        grace=seconds,
        power_off_cap=st.integers(1, 10),
        cap_window=seconds,
        cap_pause=seconds,
        message_repeat=seconds,
    ),
)


@given(policies)
def test_any_policy_survives_a_trip_through_json(policy: Policy) -> None:
    stored = json.loads(json.dumps(encode_policy(policy)))
    assert decode_policy(stored) == policy
