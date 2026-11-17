from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from support import (
    FAST,
    T0,
    FakeClock,
    ScriptedTV,
    plugin_for,
    seed_tv,
    sign_in_as_admin,
    watching,
)

from tvbalance.api.app import create_app
from tvbalance.api.routes import events_ws
from tvbalance.config import EngineConfig

URL = "/api/v1/events/ws"


@pytest.fixture
def client(engine_config: EngineConfig) -> Iterator[TestClient]:
    tv = ScriptedTV(observation=watching())
    app = create_app(
        plugins={"fake": plugin_for(tv)},
        include_testing=True,
        config=engine_config,
        clock=FakeClock(),
        supervisor_settings=FAST,
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def publish(client: TestClient, tv_id: str | None, event_type: str, **payload: Any) -> None:
    assert client.portal is not None
    client.portal.call(client.app.state.events.publish, tv_id, event_type, payload, T0)  # type: ignore[attr-defined]


def token(client: TestClient, scopes: list[str]) -> dict[str, str]:
    made = client.post("/api/v1/auth/tokens", json={"name": "ws", "scopes": scopes}).json()
    return {"Authorization": f"Bearer {made['token']}"}


def closes_with(client: TestClient, **kwargs: Any) -> int:
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(URL, **kwargs) as ws:
            ws.receive_json()
    return int(closed.value.code)


def test_anonymous_sockets_are_closed_with_4401(client: TestClient) -> None:
    client.cookies.clear()
    assert closes_with(client) == 4401


def test_events_arrive_as_they_happen(client: TestClient) -> None:
    tv_id = seed_tv(client)
    with client.websocket_connect(URL) as ws:
        publish(client, tv_id, "blocked", reason="app_blocked")
        message = ws.receive_json()
    assert message == {
        "type": "blocked",
        "tv_id": tv_id,
        "at": T0.isoformat(),
        "payload": {"reason": "app_blocked"},
    }


def test_a_new_socket_starts_with_the_status_of_every_tv(client: TestClient) -> None:
    first, second = seed_tv(client, name="One"), seed_tv(client, name="Two")
    assert client.portal is not None
    client.portal.call(client.app.state.supervisor.refresh)  # type: ignore[attr-defined]
    with client.websocket_connect(URL) as ws:
        snapshot = [ws.receive_json(), ws.receive_json()]
    assert {m["type"] for m in snapshot} == {"status"}
    assert {m["tv_id"] for m in snapshot} == {first, second}
    assert "connected" in snapshot[0]["payload"] and "decision" in snapshot[0]["payload"]


def test_an_idle_socket_gets_pings(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(events_ws, "PING_INTERVAL", 0.05)
    with client.websocket_connect(URL) as ws:
        assert ws.receive_json()["type"] == "ping"
        assert ws.receive_json()["type"] == "ping"


def test_a_token_can_listen_but_only_with_the_read_scope(client: TestClient) -> None:
    reader, controller = token(client, ["read"]), token(client, ["control"])
    client.cookies.clear()
    with client.websocket_connect(URL, headers=reader) as ws:
        publish(client, None, "engine_started")
        assert ws.receive_json()["type"] == "engine_started"
    assert closes_with(client, headers=controller) == 4403
    assert closes_with(client, headers={"Authorization": "Bearer tvb_wrong"}) == 4401


def test_a_page_on_another_site_cannot_use_the_cookie(client: TestClient) -> None:
    assert closes_with(client, headers={"Origin": "https://evil.example"}) == 4403
    with client.websocket_connect(URL, headers={"Origin": "http://testserver"}) as ws:
        publish(client, None, "engine_started")
        assert ws.receive_json()["type"] == "engine_started"


def test_a_token_is_not_bound_to_an_origin(client: TestClient) -> None:
    headers = {**token(client, ["read"]), "Origin": "https://dashboard.example"}
    client.cookies.clear()
    with client.websocket_connect(URL, headers=headers) as ws:
        publish(client, None, "engine_started")
        assert ws.receive_json()["type"] == "engine_started"


def test_signing_out_closes_the_socket(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(URL) as ws:
            assert client.post("/api/v1/auth/logout").status_code == 204
            publish(client, None, "engine_started")
            ws.receive_json()
    assert closed.value.code == 4401


def test_a_revoked_token_closes_its_socket(client: TestClient) -> None:
    headers = token(client, ["read"])
    [entry] = client.get("/api/v1/auth/tokens").json()
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(URL, headers=headers) as ws:
            assert client.delete(f"/api/v1/auth/tokens/{entry['id']}").status_code == 204
            publish(client, None, "engine_started")
            ws.receive_json()
    assert closed.value.code == 4401
