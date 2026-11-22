from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import (
    FAST,
    LICENSE_PUBLIC,
    T0,
    FakeClock,
    ScriptedTV,
    license_key,
    plugin_for,
    seed_tv,
    sign_in_as_admin,
    watching,
)

from tvbalance.api.app import create_app
from tvbalance.config import ConfigError, EngineConfig

URL = "/api/v1/license"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    config = EngineConfig.from_env(
        {
            "TVBALANCE_DATA_DIR": str(engine_config.data_dir),
            "TVBALANCE_CHECKOUT_URL": "https://shop.example.com/pro",
        }
    )
    app = create_app(
        plugins={"fake": plugin_for(ScriptedTV(observation=watching()))},
        include_testing=True,
        config=config,
        clock=clock,
        supervisor_settings=FAST,
        license_public_keys=(LICENSE_PUBLIC,),
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def test_a_new_install_is_free(client: TestClient) -> None:
    assert client.get(URL).json() == {
        "status": "none",
        "tier": "free",
        "licensee": None,
        "expires_at": None,
        "max_tvs": 1,
        "checkout_url": "https://shop.example.com/pro",
    }


def test_activating_a_key_makes_it_pro(client: TestClient) -> None:
    done = client.put(URL, json={"key": license_key(licensee="Rossi")})
    assert done.status_code == 200
    assert done.json()["tier"] == "pro" and done.json()["licensee"] == "Rossi"
    assert done.json()["max_tvs"] is None and "key" not in done.json()
    assert client.get(URL).json()["status"] == "active"


def test_an_invalid_key_is_a_422_with_the_reason(client: TestClient) -> None:
    refused = client.put(URL, json={"key": "not-a-license"})
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "invalid_license"
    assert client.get(URL).json()["tier"] == "free"


def test_an_expired_key_is_refused(client: TestClient, clock: FakeClock) -> None:
    refused = client.put(URL, json={"key": license_key(expires_at=T0 - timedelta(days=1))})
    assert refused.status_code == 422 and "expired" in refused.json()["error"]["message"]


def test_removing_the_license_goes_back_to_free(client: TestClient) -> None:
    client.put(URL, json={"key": license_key()})
    removed = client.delete(URL)
    assert removed.status_code == 200 and removed.json()["tier"] == "free"


def test_a_second_tv_is_limited_until_a_license_arrives(client: TestClient) -> None:
    first, second = seed_tv(client, name="One"), seed_tv(client, name="Two")
    assert client.portal is not None
    client.portal.call(client.app.state.supervisor.refresh)  # type: ignore[attr-defined]
    tvs = {tv["id"]: tv for tv in client.get("/api/v1/tvs").json()}
    assert sorted(tv["plan_limited"] for tv in tvs.values()) == [False, True]
    limited = next(i for i in (first, second) if tvs[i]["plan_limited"])
    assert tvs[limited]["status"] is None

    client.put(URL, json={"key": license_key()})
    assert [tv["plan_limited"] for tv in client.get("/api/v1/tvs").json()] == [False, False]
    assert client.get(f"/api/v1/tvs/{limited}").json()["plan_limited"] is False

    client.delete(URL)
    assert client.get(f"/api/v1/tvs/{limited}").json()["plan_limited"] is True


def test_reading_needs_a_login_and_changing_needs_the_full_admin(client: TestClient) -> None:
    made = client.post("/api/v1/auth/tokens", json={"name": "t", "scopes": ["read", "control"]})
    headers = {"Authorization": f"Bearer {made.json()['token']}"}
    admin_token = client.post("/api/v1/auth/tokens", json={"name": "a", "scopes": ["admin"]})
    admin_headers = {"Authorization": f"Bearer {admin_token.json()['token']}"}
    client.cookies.clear()
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=headers).status_code == 200
    for who in (headers, admin_headers):
        assert client.put(URL, json={"key": license_key()}, headers=who).status_code == 403
        assert client.delete(URL, headers=who).status_code == 403


def test_the_checkout_url_must_be_http_or_https() -> None:
    with pytest.raises(ConfigError):
        EngineConfig.from_env({"TVBALANCE_CHECKOUT_URL": "javascript:alert(1)"})
    assert EngineConfig.from_env({}).checkout_url == ""
