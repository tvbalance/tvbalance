import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from support import FAST, FakeClock, ScriptedTV, plugin_for, seed_tv, sign_in_as_admin, watching

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.errors import TVError
from tvbalance.sdk.types import AppInfo, Capability, ChannelInfo, InputInfo


def make_client(
    engine_config: EngineConfig, clock: FakeClock, tv: ScriptedTV, **plugin: object
) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": plugin_for(tv, **plugin)},  # type: ignore[arg-type]
        include_testing=True,
        config=engine_config,
        clock=clock,
        supervisor_settings=FAST,
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def tv() -> ScriptedTV:
    return ScriptedTV(
        observation=watching(),
        apps=[AppInfo("video", "Video", "http://tv.local/video.png")],
        inputs=[InputInfo("hdmi1", "HDMI 1")],
        channels=[ChannelInfo("c1", "One", "1")],
    )


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock, tv: ScriptedTV) -> Iterator[TestClient]:
    yield from make_client(engine_config, clock, tv)


def wait_connected(client: TestClient, tv_id: str) -> None:
    assert client.portal is not None
    client.portal.call(client.app.state.supervisor.refresh)  # type: ignore[attr-defined]
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        status = client.get(f"/api/v1/tvs/{tv_id}").json()["status"]
        if status is not None and status["connected"]:
            return
        time.sleep(0.02)
    raise AssertionError("the TV never connected")


def test_inventory_lists_what_the_tv_offers(client: TestClient) -> None:
    tv_id = seed_tv(client)
    wait_connected(client, tv_id)
    body = client.get(f"/api/v1/tvs/{tv_id}/inventory").json()
    assert body == {
        "apps": [{"id": "video", "name": "Video", "has_icon": True}],
        "inputs": [{"id": "hdmi1", "label": "HDMI 1"}],
        "channels": [{"id": "c1", "name": "One", "number": "1"}],
    }


def test_inventory_is_cached_for_a_few_minutes(
    client: TestClient, clock: FakeClock, tv: ScriptedTV
) -> None:
    tv_id = seed_tv(client)
    wait_connected(client, tv_id)
    first = client.get(f"/api/v1/tvs/{tv_id}/inventory").json()
    tv.apps = [AppInfo("other", "Other")]
    assert client.get(f"/api/v1/tvs/{tv_id}/inventory").json() == first
    clock.advance(minutes=6)
    assert client.get(f"/api/v1/tvs/{tv_id}/inventory").json()["apps"][0]["id"] == "other"


def test_inventory_of_an_offline_tv_is_a_conflict(
    engine_config: EngineConfig, clock: FakeClock
) -> None:
    tv = ScriptedTV(observation=watching(), connect_error=TVError("down"))
    for client in make_client(engine_config, clock, tv):
        tv_id = seed_tv(client)
        response = client.get(f"/api/v1/tvs/{tv_id}/inventory")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "tv_offline"


def test_capabilities_the_adapter_lacks_give_empty_lists(
    engine_config: EngineConfig, clock: FakeClock, tv: ScriptedTV
) -> None:
    only_apps = frozenset({Capability.LIST_APPS, Capability.FOREGROUND_APP})
    for client in make_client(engine_config, clock, tv, capabilities=only_apps):
        tv_id = seed_tv(client)
        wait_connected(client, tv_id)
        body = client.get(f"/api/v1/tvs/{tv_id}/inventory").json()
        assert len(body["apps"]) == 1 and body["inputs"] == [] and body["channels"] == []


def test_inventory_of_an_unknown_tv_is_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/tvs/nope/inventory").status_code == 404


def test_inventory_needs_the_read_scope(client: TestClient) -> None:
    tv_id = seed_tv(client)
    made = client.post("/api/v1/auth/tokens", json={"name": "c", "scopes": ["control"]}).json()
    client.cookies.clear()
    headers: dict[str, str] = {"Authorization": f"Bearer {made['token']}"}
    assert client.get(f"/api/v1/tvs/{tv_id}/inventory").status_code == 401
    assert client.get(f"/api/v1/tvs/{tv_id}/inventory", headers=headers).status_code == 403
