from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import LICENSE_PUBLIC, T0, FakeClock, license_key, seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.domain.models import ContentKey
from tvbalance.sdk.fake import PLUGIN


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": PLUGIN},
        include_testing=True,
        config=engine_config,
        clock=clock,
        license_public_keys=(LICENSE_PUBLIC,),
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
    assert client.get(f"/api/v1/tvs/{tv_id}/usage?days=367").status_code == 422


def go_pro(client: TestClient) -> None:
    assert client.put("/api/v1/license", json={"key": license_key()}).status_code == 200


def test_free_history_is_cut_to_a_week(client: TestClient) -> None:
    tv_id = seed_tv(client)
    body = client.get(f"/api/v1/tvs/{tv_id}/usage?days=30").json()
    assert len(body["days"]) == 7 and body["limited"] is True
    assert client.get(f"/api/v1/tvs/{tv_id}/usage?days=7").json()["limited"] is False


def test_pro_sees_a_long_history(client: TestClient) -> None:
    tv_id = seed_tv(client)
    go_pro(client)
    call(client, storage_of(client).usage.add_watched, tv_id, T0.date() - timedelta(days=40), 90)
    body = client.get(f"/api/v1/tvs/{tv_id}/usage?days=366").json()
    assert len(body["days"]) == 366 and body["limited"] is False
    assert body["days"][40]["watched_seconds"] == 90


def storage_of(client: TestClient):  # type: ignore[no-untyped-def]
    return client.app.state.storage  # type: ignore[attr-defined]


def seed_content(client: TestClient, tv_id: str) -> None:
    content = storage_of(client).content_usage
    day = T0.date()
    call(client, content.add, tv_id, day, ContentKey("app", "youtube"), 600)
    call(client, content.add, tv_id, day - timedelta(days=1), ContentKey("app", "youtube"), 300)
    call(client, content.add, tv_id, day, ContentKey("input", "HDMI_1"), 1200)
    call(client, content.add, tv_id, day - timedelta(days=30), ContentKey("app", "old"), 50)


def test_content_usage_ranks_what_was_viewed(client: TestClient) -> None:
    tv_id = seed_tv(client)
    seed_content(client, tv_id)
    body = client.get(f"/api/v1/tvs/{tv_id}/usage/content").json()
    assert body["first"] == "2026-11-11" and body["last"] == "2026-11-17"
    assert body["items"] == [
        {"kind": "input", "id": "HDMI_1", "seconds": 1200},
        {"kind": "app", "id": "youtube", "seconds": 900},
    ]
    assert body["limited"] is False


def test_free_content_range_is_cut_to_a_week(client: TestClient) -> None:
    tv_id = seed_tv(client)
    seed_content(client, tv_id)
    body = client.get(f"/api/v1/tvs/{tv_id}/usage/content?from=2026-10-01").json()
    assert body["first"] == "2026-11-11" and body["limited"] is True
    assert all(item["id"] != "old" for item in body["items"])


def test_pro_content_range_goes_back_further(client: TestClient) -> None:
    tv_id = seed_tv(client)
    seed_content(client, tv_id)
    go_pro(client)
    body = client.get(f"/api/v1/tvs/{tv_id}/usage/content?from=2026-10-01&to=2026-11-17").json()
    assert body["limited"] is False
    assert {"kind": "app", "id": "old", "seconds": 50} in body["items"]


def test_content_range_is_validated(client: TestClient) -> None:
    tv_id = seed_tv(client)
    backwards = client.get(f"/api/v1/tvs/{tv_id}/usage/content?from=2026-11-10&to=2026-11-01")
    assert backwards.status_code == 422
    too_long = client.get(f"/api/v1/tvs/{tv_id}/usage/content?from=2020-01-01")
    assert too_long.status_code == 422
    assert client.get("/api/v1/tvs/nope/usage/content").status_code == 404


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
