from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import T0, FakeClock, seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.fake import PLUGIN


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": PLUGIN}, include_testing=True, config=engine_config, clock=clock
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def call(client: TestClient, function, *args):  # type: ignore[no-untyped-def]
    assert client.portal is not None
    return client.portal.call(function, *args)


def test_usage_lists_today_and_the_days_before(client: TestClient) -> None:
    tv_id = seed_tv(client)
    storage = client.app.state.storage  # type: ignore[attr-defined]
    call(client, storage.usage.add_watched, tv_id, T0.date(), 1800)
    call(client, storage.usage.add_watched, tv_id, T0.date() - timedelta(days=2), 600)
    call(client, storage.usage.add_bonus, tv_id, T0.date(), 15)

    body = client.get(f"/api/v1/tvs/{tv_id}/usage").json()
    assert body["tv_id"] == tv_id and len(body["days"]) == 7
    today, yesterday, before = body["days"][:3]
    assert today == {"day": "2026-11-17", "watched_seconds": 1800, "bonus_minutes": 15}
    assert yesterday == {"day": "2026-11-16", "watched_seconds": 0, "bonus_minutes": 0}
    assert before["watched_seconds"] == 600


def test_usage_length_is_bounded(client: TestClient) -> None:
    tv_id = seed_tv(client)
    assert len(client.get(f"/api/v1/tvs/{tv_id}/usage?days=2").json()["days"]) == 2
    assert client.get(f"/api/v1/tvs/{tv_id}/usage?days=0").status_code == 422
    assert client.get(f"/api/v1/tvs/{tv_id}/usage?days=91").status_code == 422


def test_usage_of_an_unknown_tv_is_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/tvs/nope/usage").status_code == 404


def test_events_are_listed_newest_first_and_can_be_filtered(
    client: TestClient, clock: FakeClock
) -> None:
    first, second = seed_tv(client, name="One"), seed_tv(client, name="Two")
    log = client.app.state.storage.events  # type: ignore[attr-defined]
    call(client, log.append, first, "blocked", {"reason": "app_blocked"}, T0 - timedelta(hours=2))
    call(client, log.append, second, "warned", {"minutes_left": 5}, T0 - timedelta(hours=1))
    call(client, log.append, None, "engine_started", {}, T0)

    everything = client.get("/api/v1/events").json()
    assert [e["type"] for e in everything] == ["engine_started", "warned", "blocked"]
    assert everything[2]["payload"] == {"reason": "app_blocked"} and everything[2]["tv_id"] == first

    only_first = client.get("/api/v1/events", params={"tv_id": first}).json()
    assert [e["type"] for e in only_first] == ["blocked"]
    assert len(client.get("/api/v1/events", params={"limit": 1}).json()) == 1


def test_events_default_to_the_last_week(client: TestClient) -> None:
    tv_id = seed_tv(client)
    log = client.app.state.storage.events  # type: ignore[attr-defined]
    call(client, log.append, tv_id, "old", {}, T0 - timedelta(days=8))
    call(client, log.append, tv_id, "recent", {}, T0 - timedelta(days=6))
    assert [e["type"] for e in client.get("/api/v1/events").json()] == ["recent"]
    since = (T0 - timedelta(days=9)).isoformat()
    assert len(client.get("/api/v1/events", params={"since": since}).json()) == 2


def test_event_limits_are_bounded(client: TestClient) -> None:
    assert client.get("/api/v1/events?limit=0").status_code == 422
    assert client.get("/api/v1/events?limit=501").status_code == 422


def test_activity_needs_a_sign_in(client: TestClient) -> None:
    tv_id = seed_tv(client)
    client.cookies.clear()
    assert client.get("/api/v1/events").status_code == 401
    assert client.get(f"/api/v1/tvs/{tv_id}/usage").status_code == 401


def test_settings_default_to_english_and_the_system_zone(client: TestClient) -> None:
    assert client.get("/api/v1/settings").json() == {"language": "en", "timezone": None}


def test_settings_change_one_field_at_a_time(client: TestClient) -> None:
    saved = client.put("/api/v1/settings", json={"language": "it"})
    assert saved.json() == {"language": "it", "timezone": None}
    saved = client.put("/api/v1/settings", json={"timezone": "Europe/Rome"})
    assert saved.json() == {"language": "it", "timezone": "Europe/Rome"}
    assert client.get("/api/v1/settings").json() == saved.json()
    cleared = client.put("/api/v1/settings", json={"timezone": None})
    assert cleared.json() == {"language": "it", "timezone": None}


@pytest.mark.parametrize("body", [{"language": "tlh"}, {"timezone": "Mars/Olympus"}, {"x": 1}])
def test_bad_settings_are_refused(client: TestClient, body: dict[str, object]) -> None:
    response = client.put("/api/v1/settings", json=body)
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_failed"


def test_only_admins_change_settings(client: TestClient) -> None:
    made = client.post(
        "/api/v1/auth/tokens", json={"name": "ha", "scopes": ["read", "control"]}
    ).json()
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {made['token']}"}
    assert client.get("/api/v1/settings", headers=headers).status_code == 200
    assert (
        client.put("/api/v1/settings", json={"language": "it"}, headers=headers).status_code == 403
    )
