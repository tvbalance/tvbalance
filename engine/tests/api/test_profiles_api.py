from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from support import (
    FAST,
    LICENSE_PUBLIC,
    FakeClock,
    ScriptedTV,
    license_key,
    plugin_for,
    seed_tv,
    sign_in_as_admin,
    watching,
)

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig

ACTIVE = "/api/v1/profiles/active"
CALENDAR = "/api/v1/calendar"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": plugin_for(ScriptedTV(observation=watching()))},
        include_testing=True,
        config=engine_config,
        clock=clock,
        supervisor_settings=FAST,
        license_public_keys=(LICENSE_PUBLIC,),
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        assert running.portal is not None
        running.portal.call(running.app.state.storage.settings.set, "timezone", "Europe/Rome")  # type: ignore[attr-defined]
        yield running


@pytest.fixture
def policy_id(client: TestClient) -> int:
    created = client.post("/api/v1/policies", json={"name": "Holidays", "policy": {}})
    return int(created.json()["id"])


def go_pro(client: TestClient) -> None:
    assert client.put("/api/v1/license", json={"key": license_key()}).status_code == 200


def weekly(policy_id: int, **extra: Any) -> dict[str, Any]:
    return {
        "kind": "weekly",
        "policy_id": policy_id,
        "weekdays": [5, 6],
        "start": "08:00:00",
        "end": "20:00:00",
        **extra,
    }


def dated(policy_id: int, **extra: Any) -> dict[str, Any]:
    return {
        "kind": "dated",
        "policy_id": policy_id,
        "start_date": "2026-12-24",
        "end_date": "2027-01-06",
        **extra,
    }


# --- active profile -------------------------------------------------------------------------


def test_nothing_is_active_at_first(client: TestClient) -> None:
    got = client.get(ACTIVE)
    assert got.status_code == 200
    assert got.json() == {"effective": False, "activation": None}


def test_activating_a_profile_for_a_while(client: TestClient, policy_id: int) -> None:
    tv_id = seed_tv(client)
    go_pro(client)
    done = client.post(
        ACTIVE, json={"policy_id": policy_id, "minutes": 90, "excluded_tv_ids": [tv_id]}
    )
    assert done.status_code == 200
    body = client.get(ACTIVE).json()
    assert body["effective"] is True
    activation = body["activation"]
    assert activation["policy_id"] == policy_id and activation["name"] == "Holidays"
    assert activation["excluded_tv_ids"] == [tv_id] and activation["source"] == "manual"
    assert activation == done.json()


def test_a_profile_can_last_until_midnight(client: TestClient, policy_id: int) -> None:
    done = client.post(ACTIVE, json={"policy_id": policy_id, "until_midnight": True})
    assert done.status_code == 200
    assert done.json()["ends_at"].startswith("2026-11-17T23:00:00")  # Rome midnight, in UTC


def test_a_profile_needs_exactly_one_duration(client: TestClient, policy_id: int) -> None:
    both = {"policy_id": policy_id, "minutes": 5, "until_midnight": True}
    assert client.post(ACTIVE, json=both).status_code == 422
    assert client.post(ACTIVE, json={"policy_id": policy_id}).status_code == 422


def test_an_unknown_policy_or_tv_is_a_404(client: TestClient, policy_id: int) -> None:
    assert client.post(ACTIVE, json={"policy_id": 999, "minutes": 5}).status_code == 404
    body = {"policy_id": policy_id, "minutes": 5, "excluded_tv_ids": ["nope"]}
    assert client.post(ACTIVE, json=body).status_code == 404


def test_stopping_the_profile(client: TestClient, policy_id: int) -> None:
    client.post(ACTIVE, json={"policy_id": policy_id, "minutes": 5})
    assert client.delete(ACTIVE).status_code == 204
    assert client.get(ACTIVE).json()["activation"] is None
    assert client.delete(ACTIVE).status_code == 204  # nothing to stop is fine


def test_a_new_profile_replaces_the_one_in_force(client: TestClient, policy_id: int) -> None:
    other = client.post("/api/v1/policies", json={"name": "Weekend", "policy": {}}).json()["id"]
    client.post(ACTIVE, json={"policy_id": policy_id, "minutes": 5})
    client.post(ACTIVE, json={"policy_id": other, "minutes": 5})
    assert client.get(ACTIVE).json()["activation"]["policy_id"] == other


def test_the_active_profile_shows_in_the_tv_status(client: TestClient, policy_id: int) -> None:
    tv_id = seed_tv(client)
    go_pro(client)
    client.post(ACTIVE, json={"policy_id": policy_id, "minutes": 30})
    import time

    deadline = time.monotonic() + 3
    status: Any = None
    while time.monotonic() < deadline:
        status = client.get(f"/api/v1/tvs/{tv_id}").json()["status"]
        if status and status["active_profile"]:
            break
        time.sleep(0.02)
    assert status["active_profile"]["policy_id"] == policy_id
    assert status["active_profile"]["name"] == "Holidays"
    assert status["active_profile"]["source"] == "manual"


def test_a_pin_without_control_cannot_activate(client: TestClient, policy_id: int) -> None:
    client.cookies.clear()
    assert client.post(ACTIVE, json={"policy_id": policy_id, "minutes": 5}).status_code == 401


# --- calendar -------------------------------------------------------------------------------


def test_the_calendar_starts_empty_and_says_whether_it_is_in_effect(client: TestClient) -> None:
    assert client.get(CALENDAR).json() == {"effective": False, "entries": []}
    go_pro(client)
    assert client.get(CALENDAR).json()["effective"] is True


def test_entries_are_added_listed_changed_and_removed(client: TestClient, policy_id: int) -> None:
    tv_id = seed_tv(client)
    first = client.post(CALENDAR, json=weekly(policy_id, excluded_tv_ids=[tv_id]))
    second = client.post(CALENDAR, json=dated(policy_id))
    assert first.status_code == 201 and second.status_code == 201
    entries = client.get(CALENDAR).json()["entries"]
    assert [e["id"] for e in entries] == [first.json()["id"], second.json()["id"]]
    assert entries[0]["weekdays"] == [5, 6] and entries[0]["excluded_tv_ids"] == [tv_id]
    assert entries[0]["start"].startswith("08:00") and entries[1]["start_date"] == "2026-12-24"

    changed = client.put(f"{CALENDAR}/{first.json()['id']}", json=dated(policy_id))
    assert changed.status_code == 200 and changed.json()["kind"] == "dated"
    assert client.delete(f"{CALENDAR}/{second.json()['id']}").status_code == 204
    assert len(client.get(CALENDAR).json()["entries"]) == 1


def test_bad_entries_are_422(client: TestClient, policy_id: int) -> None:
    for bad in (
        weekly(policy_id, weekdays=[]),
        weekly(policy_id, weekdays=[7]),
        weekly(policy_id, weekdays=[1, 1]),
        dated(policy_id, start_date="2027-01-07"),
        {**dated(policy_id), "kind": "yearly"},
    ):
        assert client.post(CALENDAR, json=bad).status_code == 422, bad


def test_entries_must_name_known_things(client: TestClient, policy_id: int) -> None:
    assert client.post(CALENDAR, json=weekly(999)).status_code == 404
    unknown_tv = weekly(policy_id, excluded_tv_ids=["nope"])
    assert client.post(CALENDAR, json=unknown_tv).status_code == 404
    assert client.put(f"{CALENDAR}/999", json=weekly(policy_id)).status_code == 404
    assert client.delete(f"{CALENDAR}/999").status_code == 404
