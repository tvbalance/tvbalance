from collections.abc import Iterator
from time import monotonic, sleep
from typing import Any

import pytest
from fastapi.testclient import TestClient
from support import (
    FAST,
    FakeClock,
    PairableTV,
    ScriptedPairing,
    plugin_for,
    seed_tv,
    sign_in_as_admin,
)

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.types import PairingState


def make_client(
    engine_config: EngineConfig, tv: PairableTV, clock: FakeClock
) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": plugin_for(tv)},
        include_testing=True,
        config=engine_config,
        clock=clock,
        supervisor_settings=FAST,
        pairing_poll_interval=0.01,
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def tv() -> PairableTV:
    return PairableTV(flow=ScriptedPairing([PairingState.WAITING_FOR_USER, PairingState.COMPLETED]))


@pytest.fixture
def client(engine_config: EngineConfig, tv: PairableTV, clock: FakeClock) -> Iterator[TestClient]:
    yield from make_client(engine_config, tv, clock)


def begin(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/pairings", json={"adapter_id": "fake", "host": "tv.local", **body})


def settle(client: TestClient, pairing_id: str, states: set[str] | None = None) -> dict[str, Any]:
    """Poll the pairing until it leaves ``waiting_for_user`` (or reaches one of ``states``)."""
    deadline = monotonic() + 3
    while monotonic() < deadline:
        body: dict[str, Any] = client.get(f"/api/v1/pairings/{pairing_id}").json()
        if body["state"] in (states or {"completed", "failed", "expired"}):
            return body
        sleep(0.01)
    raise AssertionError("the pairing never settled")


def test_pairing_stores_the_tv_once_the_user_accepts(client: TestClient, tv: PairableTV) -> None:
    started = begin(client, name="Living room")
    assert started.status_code == 201
    body = started.json()
    assert body["state"] == "waiting_for_user"
    assert body["adapter_id"] == "fake" and body["host"] == "tv.local" and body["tv_id"] is None

    done = settle(client, body["id"])
    assert done["state"] == "completed" and done["tv_id"]

    listed = client.get("/api/v1/tvs").json()
    assert [(t["id"], t["name"], t["host"], t["adapter_id"]) for t in listed] == [
        (done["tv_id"], "Living room", "tv.local", "fake")
    ]
    assert listed[0]["policy_id"] is None and listed[0]["needs_pairing"] is False
    storage = client.app.state.storage  # type: ignore[attr-defined]
    assert client.portal is not None
    record = client.portal.call(storage.tvs.get, done["tv_id"])
    assert record.credentials == {"client_key": "paired-key"}


def test_the_new_tv_is_watched_and_announced(client: TestClient) -> None:
    done = settle(client, begin(client).json()["id"])
    events = client.get("/api/v1/events", params={"tv_id": done["tv_id"]}).json()
    assert [e["type"] for e in events if e["type"] == "tv_added"] == ["tv_added"]
    deadline = monotonic() + 3
    while monotonic() < deadline:
        status = client.get(f"/api/v1/tvs/{done['tv_id']}").json()["status"]
        if status and status["connected"]:
            return
        sleep(0.02)
    raise AssertionError("the supervisor never started watching the new TV")


def test_without_a_name_the_tv_is_called_after_its_adapter(client: TestClient) -> None:
    done = settle(client, begin(client).json()["id"])
    assert client.get(f"/api/v1/tvs/{done['tv_id']}").json()["name"] == "Fake TV"


def test_a_refused_pairing_stores_nothing(engine_config: EngineConfig, clock: FakeClock) -> None:
    refused = PairableTV(flow=ScriptedPairing([PairingState.FAILED]))
    for client in make_client(engine_config, refused, clock):
        done = settle(client, begin(client).json()["id"])
        assert done["state"] == "failed" and done["tv_id"] is None
        assert client.get("/api/v1/tvs").json() == []


def test_asking_again_for_the_same_host_returns_the_pending_pairing(
    engine_config: EngineConfig, clock: FakeClock
) -> None:
    waiting = PairableTV(flow=ScriptedPairing([]))
    for client in make_client(engine_config, waiting, clock):
        first = begin(client).json()
        second = begin(client)
        assert second.status_code == 201 and second.json()["id"] == first["id"]
        other = begin(client, host="other.local").json()
        assert other["id"] != first["id"]


def test_a_tv_that_is_already_added_cannot_be_added_twice(client: TestClient) -> None:
    seed_tv(client, host="tv.local")
    clash = begin(client)
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "tv_exists"
    assert begin(client, host="TV.LOCAL").status_code == 409


def test_an_unknown_adapter_is_not_found(client: TestClient) -> None:
    missing = client.post("/api/v1/pairings", json={"adapter_id": "nope", "host": "tv.local"})
    assert missing.status_code == 404


@pytest.mark.parametrize(
    "host", ["", "http://tv.local", "tv.local:3001", "tv.local/path", "a b", "-bad.local"]
)
def test_the_host_must_be_a_bare_name_or_address(client: TestClient, host: str) -> None:
    assert begin(client, host=host).status_code == 422


@pytest.mark.parametrize("host", ["198.51.100.20", "tv-1.home.arpa", "fe80::1", "LivingRoom"])
def test_names_and_addresses_are_accepted(client: TestClient, host: str) -> None:
    assert begin(client, host=host).status_code == 201


def test_an_unknown_pairing_is_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/pairings/nope").status_code == 404


def test_pairing_needs_an_admin(engine_config: EngineConfig) -> None:
    app = create_app(plugins={}, config=engine_config)
    with TestClient(app) as anonymous:
        assert (
            anonymous.post("/api/v1/pairings", json={"adapter_id": "x", "host": "h"}).status_code
            == 401
        )
