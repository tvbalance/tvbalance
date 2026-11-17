from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from support import seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.fake import PLUGIN


@pytest.fixture
def client(engine_config: EngineConfig) -> Iterator[TestClient]:
    app = create_app(plugins={"fake": PLUGIN}, include_testing=True, config=engine_config)
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def bearer_for(client: TestClient, scopes: list[str]) -> dict[str, str]:
    token = client.post("/api/v1/auth/tokens", json={"name": "t", "scopes": scopes}).json()["token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def test_tvs_need_a_sign_in(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get("/api/v1/tvs").status_code == 401


def test_no_tvs_yet(client: TestClient) -> None:
    assert client.get("/api/v1/tvs").json() == []


def test_a_tv_is_listed_with_its_live_status(client: TestClient) -> None:
    tv_id = seed_tv(client)
    assert client.portal is not None
    client.portal.call(client.app.state.supervisor.refresh)  # type: ignore[attr-defined]
    [tv] = client.get("/api/v1/tvs").json()
    assert tv["id"] == tv_id and tv["name"] == "Living room" and tv["adapter_id"] == "fake"
    assert tv["enabled"] is True and tv["policy_id"] is None and tv["needs_pairing"] is False
    assert tv["status"] is not None and "decision" in tv["status"]
    assert "credentials" not in tv  # secrets never leave the engine
    assert client.get(f"/api/v1/tvs/{tv_id}").json()["id"] == tv_id


def test_an_unknown_tv_is_not_found(client: TestClient) -> None:
    for response in (
        client.get("/api/v1/tvs/nope"),
        client.patch("/api/v1/tvs/nope", json={"name": "x"}),
        client.delete("/api/v1/tvs/nope"),
    ):
        assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_a_tv_can_be_renamed_disabled_and_given_a_policy(client: TestClient) -> None:
    tv_id = seed_tv(client)
    policy = client.post("/api/v1/policies", json={"name": "School"}).json()["id"]
    changed = client.patch(
        f"/api/v1/tvs/{tv_id}", json={"name": "Kids", "enabled": False, "policy_id": policy}
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert (body["name"], body["enabled"], body["policy_id"]) == ("Kids", False, policy)
    assert body["status"] is None  # disabled: nobody is watching it

    detached = client.patch(f"/api/v1/tvs/{tv_id}", json={"policy_id": None}).json()
    assert detached["policy_id"] is None and detached["name"] == "Kids"


def test_a_missing_policy_cannot_be_assigned(client: TestClient) -> None:
    tv_id = seed_tv(client)
    response = client.patch(f"/api/v1/tvs/{tv_id}", json={"policy_id": 999})
    assert response.status_code == 404
    assert client.get(f"/api/v1/tvs/{tv_id}").json()["policy_id"] is None


def test_updates_reject_unknown_fields(client: TestClient) -> None:
    tv_id = seed_tv(client)
    assert client.patch(f"/api/v1/tvs/{tv_id}", json={"host": "x"}).status_code == 422


def test_a_tv_can_be_removed(client: TestClient) -> None:
    tv_id = seed_tv(client)
    assert client.delete(f"/api/v1/tvs/{tv_id}").status_code == 204
    assert client.get("/api/v1/tvs").json() == []


def test_a_control_token_reads_but_cannot_change_tvs(client: TestClient) -> None:
    tv_id = seed_tv(client)
    headers = bearer_for(client, ["read", "control"])
    assert client.get("/api/v1/tvs", headers=headers).status_code == 200
    renamed = client.patch(f"/api/v1/tvs/{tv_id}", json={"name": "x"}, headers=headers)
    assert renamed.status_code == 403
    assert client.delete(f"/api/v1/tvs/{tv_id}", headers=headers).status_code == 403
