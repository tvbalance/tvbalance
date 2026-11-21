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


@pytest.fixture
def waiting() -> PairableTV:
    return PairableTV(flow=ScriptedPairing([]))


def test_a_pairing_nobody_accepts_expires(
    engine_config: EngineConfig, waiting: PairableTV, clock: FakeClock
) -> None:
    for client in make_client(engine_config, waiting, clock):
        started = begin(client).json()
        clock.advance(minutes=4)
        assert settle(client, started["id"])["state"] == "expired"
        assert waiting.flow.cancelled
        assert client.get("/api/v1/tvs").json() == []
        assert begin(client).json()["id"] != started["id"]  # a new attempt is allowed


def test_leaving_the_wizard_cancels_the_pairing(
    engine_config: EngineConfig, waiting: PairableTV, clock: FakeClock
) -> None:
    for client in make_client(engine_config, waiting, clock):
        started = begin(client).json()
        assert client.delete(f"/api/v1/pairings/{started['id']}").status_code == 204
        assert waiting.flow.cancelled
        assert client.get(f"/api/v1/pairings/{started['id']}").status_code == 404
        assert client.delete(f"/api/v1/pairings/{started['id']}").status_code == 404
        assert client.get("/api/v1/tvs").json() == []


def test_a_finished_pairing_can_be_dismissed_without_removing_the_tv(client: TestClient) -> None:
    done = settle(client, begin(client).json()["id"])
    assert client.delete(f"/api/v1/pairings/{done['id']}").status_code == 204
    assert len(client.get("/api/v1/tvs").json()) == 1


def test_stopping_the_engine_cancels_pending_pairings(
    engine_config: EngineConfig, waiting: PairableTV, clock: FakeClock
) -> None:
    for client in make_client(engine_config, waiting, clock):
        begin(client)
    assert waiting.flow.cancelled


def test_a_finished_pairing_is_forgotten_after_a_while(
    client: TestClient, clock: FakeClock
) -> None:
    done = settle(client, begin(client).json()["id"])
    clock.advance(minutes=11)
    assert client.get(f"/api/v1/pairings/{done['id']}").status_code == 404
    assert len(client.get("/api/v1/tvs").json()) == 1


def stored_key(client: TestClient, tv_id: str) -> str:
    storage = client.app.state.storage  # type: ignore[attr-defined]
    assert client.portal is not None
    record = client.portal.call(storage.tvs.get, tv_id)
    return str(record.credentials["client_key"])


def test_pairing_again_replaces_the_key_and_restarts_the_worker(
    client: TestClient, tv: PairableTV
) -> None:
    tv_id = seed_tv(client)
    assert stored_key(client, tv_id) == "k"

    started = client.post("/api/v1/pairings", json={"adapter_id": "fake", "tv_id": tv_id})
    assert started.status_code == 201 and started.json()["tv_id"] == tv_id
    done = settle(client, started.json()["id"])

    assert done["state"] == "completed" and done["tv_id"] == tv_id
    assert stored_key(client, tv_id) == "paired-key"
    assert len(client.get("/api/v1/tvs").json()) == 1
    types = [e["type"] for e in client.get("/api/v1/events", params={"tv_id": tv_id}).json()]
    assert "tv_paired" in types and "tv_added" not in types
    deadline = monotonic() + 3
    while tv.connect_calls == 0 and monotonic() < deadline:
        sleep(0.01)
    assert tv.connect_calls > 0


def test_pairing_again_checks_the_tv_and_its_adapter(
    engine_config: EngineConfig, tv: PairableTV, clock: FakeClock
) -> None:
    app = create_app(
        plugins={"fake": plugin_for(tv), "other": plugin_for(tv, adapter_id="other")},
        include_testing=True,
        config=engine_config,
        clock=clock,
        supervisor_settings=FAST,
        pairing_poll_interval=0.01,
    )
    with TestClient(app) as client:
        sign_in_as_admin(client)
        tv_id = seed_tv(client)
        missing = client.post("/api/v1/pairings", json={"adapter_id": "fake", "tv_id": "nope"})
        assert missing.status_code == 404
        wrong = client.post("/api/v1/pairings", json={"adapter_id": "other", "tv_id": tv_id})
        assert wrong.status_code == 409
        assert wrong.json()["error"]["code"] == "adapter_mismatch"


def test_a_new_pairing_needs_an_adapter_and_a_host(client: TestClient) -> None:
    assert client.post("/api/v1/pairings", json={"adapter_id": "fake"}).status_code == 422
    assert client.post("/api/v1/pairings", json={"host": "tv.local"}).status_code == 422
    assert client.post("/api/v1/pairings", json={}).status_code == 422


def test_pairing_needs_an_admin(engine_config: EngineConfig) -> None:
    app = create_app(plugins={}, config=engine_config)
    with TestClient(app) as anonymous:
        assert (
            anonymous.post("/api/v1/pairings", json={"adapter_id": "x", "host": "h"}).status_code
            == 401
        )
