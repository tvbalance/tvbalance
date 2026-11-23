from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from support import seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.fake import PLUGIN

WEEKDAY = {"start": "15:00:00", "end": "19:30:00"}
SCHOOL: dict[str, Any] = {
    "schedule": {"windows": {"0": [WEEKDAY], "1": [WEEKDAY]}, "special_days": {}},
    "daily_budget_minutes": 90,
    "blocked_apps": ["tiktok"],
    "always_allowed_apps": ["classroom"],
    "fallback": {"kind": "app", "id": "classroom"},
    "warn_at_minutes": [10, 5],
}


@pytest.fixture
def client(engine_config: EngineConfig) -> Iterator[TestClient]:
    app = create_app(plugins={"fake": PLUGIN}, include_testing=True, config=engine_config)
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def issue_codes(response: Any) -> set[str]:
    return {d["code"] for d in response.json()["error"]["details"]}


def create(client: TestClient, name: str = "School") -> int:
    response = client.post("/api/v1/policies", json={"name": name, "policy": SCHOOL})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def test_a_policy_round_trips(client: TestClient) -> None:
    created = client.post("/api/v1/policies", json={"name": "School", "policy": SCHOOL})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "School" and body["tv_ids"] == []
    assert body["policy"]["daily_budget_minutes"] == 90
    assert body["policy"]["schedule"]["windows"]["0"] == [WEEKDAY]
    assert body["policy"]["fallback"] == {"kind": "app", "id": "classroom"}
    assert client.get(f"/api/v1/policies/{body['id']}").json() == body
    assert client.get("/api/v1/policies").json() == [body]


def test_defaults_make_a_policy_that_blocks_everything(client: TestClient) -> None:
    body = client.post("/api/v1/policies", json={"name": "Closed"}).json()
    assert body["policy"]["schedule"]["windows"] == {}
    assert body["policy"]["warn_at_minutes"] == [10, 5]


def test_saving_changes_the_name_and_the_rules(client: TestClient) -> None:
    policy_id = create(client, "A")
    saved = client.put(
        f"/api/v1/policies/{policy_id}",
        json={"name": "B", "policy": {**SCHOOL, "daily_budget_minutes": 30}},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["name"] == "B" and saved.json()["policy"]["daily_budget_minutes"] == 30
    kept = client.put(f"/api/v1/policies/{policy_id}", json={"policy": SCHOOL}).json()
    assert kept["name"] == "B"


def test_inconsistent_policies_say_what_is_wrong(client: TestClient) -> None:
    bad = {
        **SCHOOL,
        "blocked_apps": ["classroom"],  # also always allowed, and the fallback
        "warn_at_minutes": [5, 5],
        "daily_budget_minutes": -1,
    }
    response = client.post("/api/v1/policies", json={"name": "Bad", "policy": bad})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    expected = {"conflicting_lists", "invalid_warn_threshold", "negative_budget"}
    assert issue_codes(response) >= expected
    assert client.get("/api/v1/policies").json() == []  # nothing was saved


def test_advanced_budgets_round_trip(client: TestClient) -> None:
    advanced = {
        **SCHOOL,
        "weekday_budget_minutes": {"5": 180},
        "app_budgets": [{"name": "Games", "apps": ["roblox"], "minutes": 45}],
        "rollover_max_minutes": 30,
    }
    created = client.post("/api/v1/policies", json={"name": "Adv", "policy": advanced})
    assert created.status_code == 201
    stored = client.get(f"/api/v1/policies/{created.json()['id']}").json()["policy"]
    assert stored["weekday_budget_minutes"] == {"5": 180}
    assert stored["app_budgets"] == [{"name": "Games", "apps": ["roblox"], "minutes": 45}]
    assert stored["rollover_max_minutes"] == 30


def test_invalid_advanced_budgets_are_refused(client: TestClient) -> None:
    bad = {
        **SCHOOL,
        "weekday_budget_minutes": {"9": 60},
        "app_budgets": [
            {"name": "Games", "apps": [], "minutes": 10},
            {"name": "Games", "apps": ["a"], "minutes": 10},
        ],
        "rollover_max_minutes": -1,
    }
    response = client.post("/api/v1/policies", json={"name": "Bad", "policy": bad})
    assert response.status_code == 422
    expected = {"invalid_weekday", "duplicate_app_budget", "empty_app_budget", "negative_budget"}
    assert issue_codes(response) >= expected


def test_overlapping_windows_are_refused(client: TestClient) -> None:
    overlap = {"schedule": {"windows": {"0": [WEEKDAY, {"start": "18:00:00", "end": "20:00:00"}]}}}
    response = client.post("/api/v1/policies", json={"name": "Bad", "policy": overlap})
    assert response.status_code == 422 and "overlapping_windows" in issue_codes(response)


@pytest.mark.parametrize(
    "policy",
    [
        {"schedule": {"windows": {"7": [WEEKDAY]}}},
        {"fallback": {"kind": "app"}},
        {"fallback": {"kind": "home", "id": "x"}},
        {"escalation": {"grace": -1}},
        {"surprise": True},
    ],
)
def test_malformed_policies_are_refused(client: TestClient, policy: dict[str, Any]) -> None:
    response = client.post("/api/v1/policies", json={"name": "Bad", "policy": policy})
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_failed"


def test_the_home_screen_is_a_fallback_without_an_id(client: TestClient) -> None:
    body = {"name": "Home", "policy": {"fallback": {"kind": "home"}}}
    created = client.post("/api/v1/policies", json=body)
    assert created.status_code == 201, created.text
    assert created.json()["policy"]["fallback"]["kind"] == "home"


def test_unknown_policies_are_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/policies/999").status_code == 404
    assert client.put("/api/v1/policies/999", json={"policy": SCHOOL}).status_code == 404


def test_a_policy_lists_the_tvs_that_use_it(client: TestClient) -> None:
    tv_id = seed_tv(client)
    policy_id = create(client)
    client.patch(f"/api/v1/tvs/{tv_id}", json={"policy_id": policy_id})
    assert client.get(f"/api/v1/policies/{policy_id}").json()["tv_ids"] == [tv_id]
    saved = client.put(f"/api/v1/policies/{policy_id}", json={"policy": SCHOOL})
    assert saved.status_code == 200 and saved.json()["tv_ids"] == [tv_id]


def test_only_admins_write_policies(client: TestClient) -> None:
    body = {"name": "ha", "scopes": ["read", "control"]}
    token = client.post("/api/v1/auth/tokens", json=body).json()["token"]
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/policies", headers=headers).status_code == 200
    assert client.post("/api/v1/policies", json={"name": "x"}, headers=headers).status_code == 403
