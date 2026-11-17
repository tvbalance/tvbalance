import time
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from support import FAST, T0, FakeClock, ScriptedTV, plugin_for, seed_tv, sign_in_as_admin, watching

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig

ALL_DAY = {"start": "00:00:00", "end": "00:00:00"}
OPEN: dict[str, Any] = {"schedule": {"windows": {str(day): [ALL_DAY] for day in range(7)}}}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    tv = ScriptedTV(observation=watching())
    app = create_app(
        plugins={"fake": plugin_for(tv)},
        include_testing=True,
        config=engine_config,
        clock=clock,
        supervisor_settings=FAST,
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        assert running.portal is not None
        running.portal.call(running.app.state.storage.settings.set, "timezone", "Europe/Rome")  # type: ignore[attr-defined]
        yield running


@pytest.fixture
def tv_id(client: TestClient) -> str:
    """A TV under an all-day policy, so only parent controls can change what it is told."""
    policy = client.post("/api/v1/policies", json={"name": "Open", "policy": OPEN}).json()["id"]
    tv_id = seed_tv(client)
    client.patch(f"/api/v1/tvs/{tv_id}", json={"policy_id": policy})
    wait_for(client, tv_id, lambda s: s["decision"] is not None)
    return tv_id


def wait_for(
    client: TestClient, tv_id: str, check: Callable[[dict[str, Any]], bool], within: float = 3.0
) -> dict[str, Any]:
    deadline = time.monotonic() + within
    last: Any = None
    while time.monotonic() < deadline:
        last = client.get(f"/api/v1/tvs/{tv_id}").json()["status"]
        if last is not None and check(last):
            return dict(last)
        time.sleep(0.02)
    raise AssertionError(f"the TV never reached the expected state; last status: {last}")


def blocked_by_override(status: dict[str, Any]) -> bool:
    decision = status["decision"]
    return bool(decision) and decision["kind"] == "block" and decision["reason"] == "override"


def test_the_policy_alone_allows_viewing(client: TestClient, tv_id: str) -> None:
    status = client.get(f"/api/v1/tvs/{tv_id}").json()["status"]
    assert status["decision"]["kind"] != "block"


def test_a_block_override_takes_effect_at_once_and_can_be_lifted(
    client: TestClient, tv_id: str, clock: FakeClock
) -> None:
    response = client.post(f"/api/v1/tvs/{tv_id}/override", json={"allow": False, "minutes": 5})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allow"] is False
    assert body["until"] == (T0 + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    wait_for(client, tv_id, blocked_by_override)

    assert client.delete(f"/api/v1/tvs/{tv_id}/override").status_code == 204
    wait_for(client, tv_id, lambda s: not blocked_by_override(s))


def test_an_override_expires_by_itself(client: TestClient, tv_id: str, clock: FakeClock) -> None:
    client.post(f"/api/v1/tvs/{tv_id}/override", json={"allow": False, "minutes": 5})
    wait_for(client, tv_id, blocked_by_override)
    clock.advance(minutes=6)
    wait_for(client, tv_id, lambda s: not blocked_by_override(s))


def test_until_midnight_ends_at_the_household_midnight(client: TestClient, tv_id: str) -> None:
    body = client.post(
        f"/api/v1/tvs/{tv_id}/override", json={"allow": True, "until_midnight": True}
    ).json()
    # 18:00 in Rome on 2026-11-17 (UTC+1): the next midnight is 23:00 UTC the same day.
    assert body["until"].startswith("2026-11-17T23:00:00")


@pytest.mark.parametrize(
    "body",
    [
        {"allow": True},
        {"allow": True, "minutes": 5, "until_midnight": True},
        {"allow": True, "minutes": 0},
        {"allow": True, "minutes": 24 * 60 + 1},
        {"minutes": 5},
    ],
)
def test_an_override_needs_exactly_one_duration(
    client: TestClient, tv_id: str, body: dict[str, Any]
) -> None:
    response = client.post(f"/api/v1/tvs/{tv_id}/override", json=body)
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_failed"


def test_a_pause_blocks_for_half_an_hour_unless_told_otherwise(
    client: TestClient, tv_id: str
) -> None:
    body = client.post(f"/api/v1/tvs/{tv_id}/pause", json={}).json()
    assert body["allow"] is False
    assert body["until"] == (T0 + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
    wait_for(client, tv_id, blocked_by_override)
    longer = client.post(f"/api/v1/tvs/{tv_id}/pause", json={"minutes": 90}).json()
    assert longer["until"] == (T0 + timedelta(minutes=90)).isoformat().replace("+00:00", "Z")


def test_bonus_minutes_add_up_for_the_day(client: TestClient, tv_id: str) -> None:
    first = client.post(f"/api/v1/tvs/{tv_id}/bonus", json={"minutes": 15})
    assert first.status_code == 200, first.text
    assert first.json() == {"day": "2026-11-17", "bonus_minutes": 15}
    assert client.post(f"/api/v1/tvs/{tv_id}/bonus", json={"minutes": 10}).json() == {
        "day": "2026-11-17",
        "bonus_minutes": 25,
    }


@pytest.mark.parametrize("minutes", [0, -5, 241])
def test_bonus_is_bounded(client: TestClient, tv_id: str, minutes: int) -> None:
    response = client.post(f"/api/v1/tvs/{tv_id}/bonus", json={"minutes": minutes})
    assert response.status_code == 422


def test_unknown_tvs_are_not_found(client: TestClient) -> None:
    for response in (
        client.post("/api/v1/tvs/nope/override", json={"allow": True, "minutes": 5}),
        client.delete("/api/v1/tvs/nope/override"),
        client.post("/api/v1/tvs/nope/bonus", json={"minutes": 5}),
        client.post("/api/v1/tvs/nope/pause", json={}),
    ):
        assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_controls_need_the_control_scope(client: TestClient, tv_id: str) -> None:
    def token(scopes: list[str]) -> dict[str, str]:
        made = client.post("/api/v1/auth/tokens", json={"name": "t", "scopes": scopes}).json()
        return {"Authorization": f"Bearer {made['token']}"}

    read_only, control = token(["read"]), token(["control"])
    client.cookies.clear()
    path = f"/api/v1/tvs/{tv_id}/pause"
    assert client.post(path, json={}).status_code == 401
    assert client.post(path, json={}, headers=read_only).status_code == 403
    assert client.post(path, json={}, headers=control).status_code == 200
