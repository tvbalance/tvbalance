from copy import deepcopy
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tvbalance.domain.enforcement import EnforcementState
from tvbalance.infra.db.state_codec import StateDecodeError, decode_state, encode_state

ROME = timezone(timedelta(hours=1))
T0 = datetime(2026, 11, 17, 18, 30, 5, tzinfo=ROME)

FULL = EnforcementState(
    day=date(2026, 11, 17),
    warned=frozenset({10, 5}),
    episode_started=T0,
    acted_at=T0 + timedelta(seconds=3),
    last_message_at=T0 + timedelta(seconds=63),
    redirected=True,
    unavailable_reported=True,
    power_offs=(T0 - timedelta(minutes=4), T0 - timedelta(minutes=1)),
    paused_until=T0 + timedelta(minutes=10),
)

offsets = st.integers(min_value=-12 * 60, max_value=14 * 60).map(
    lambda minutes: timezone(timedelta(minutes=minutes))
)
moments = st.datetimes(
    min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1), timezones=offsets
)
states = st.builds(
    EnforcementState,
    day=st.none() | st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1)),
    warned=st.frozensets(st.integers(min_value=0, max_value=240), max_size=6),
    episode_started=st.none() | moments,
    acted_at=st.none() | moments,
    last_message_at=st.none() | moments,
    redirected=st.booleans(),
    unavailable_reported=st.booleans(),
    power_offs=st.lists(moments, max_size=5).map(tuple),
    paused_until=st.none() | moments,
)


def test_the_default_state_round_trips() -> None:
    assert decode_state(encode_state(EnforcementState())) == EnforcementState()


def test_a_full_state_round_trips() -> None:
    assert decode_state(encode_state(FULL)) == FULL


@given(states)
def test_any_state_round_trips(state: EnforcementState) -> None:
    assert decode_state(encode_state(state)) == state


def test_the_document_is_plain_json() -> None:
    doc = encode_state(FULL)
    assert doc["version"] == 1
    assert doc["day"] == "2026-11-17"
    assert doc["warned"] == [5, 10]
    assert doc["episode_started"] == "2026-11-17T18:30:05+01:00"


def test_the_encoding_is_deterministic() -> None:
    assert encode_state(FULL) == encode_state(FULL)


def test_utc_moments_keep_their_instant() -> None:
    state = EnforcementState(paused_until=datetime(2026, 11, 17, 18, 0, tzinfo=UTC))
    assert decode_state(encode_state(state)) == state


@pytest.mark.parametrize("doc", [None, [], "state", {}, {"version": 2}, {"version": "1"}])
def test_unknown_documents_are_rejected(doc: Any) -> None:
    with pytest.raises(StateDecodeError):
        decode_state(doc)


def _broken(**changes: Any) -> dict[str, Any]:
    doc = deepcopy(encode_state(FULL))
    doc.update(changes)
    return doc


@pytest.mark.parametrize(
    "doc",
    [
        _broken(day="not a date"),
        _broken(warned="10"),
        _broken(warned=[True]),
        _broken(redirected="yes"),
        _broken(unavailable_reported=None),
        _broken(episode_started="2026-11-17T18:30:05"),  # no offset
        _broken(power_offs=["2026-11-17T18:30:05"]),
        _broken(power_offs="never"),
        _broken(paused_until=5),
    ],
)
def test_malformed_documents_are_rejected(doc: dict[str, Any]) -> None:
    with pytest.raises(StateDecodeError):
        decode_state(doc)


def test_a_missing_field_is_rejected() -> None:
    doc = encode_state(FULL)
    del doc["acted_at"]
    with pytest.raises(StateDecodeError):
        decode_state(doc)
