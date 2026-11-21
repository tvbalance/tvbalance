import asyncio
import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from support import FakeClock, seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.infra.webpush import PushTarget, SendResult
from tvbalance.sdk.fake import PLUGIN

KEY = "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
ENDPOINT = "https://push.example.net/send/abc"


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[PushTarget, dict[str, str]]] = []
        self.result = SendResult.DELIVERED

    async def send(
        self, target: PushTarget, payload: bytes, *, ttl: int = 0, urgency: str = ""
    ) -> SendResult:
        self.sent.append((target, json.loads(payload)))
        return self.result


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()


@pytest.fixture
def client(engine_config: EngineConfig, sender: FakeSender) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": PLUGIN}, include_testing=True, config=engine_config, clock=FakeClock()
    )
    with TestClient(app) as running:
        app.state.push._sender = sender
        sign_in_as_admin(running)
        yield running


def body(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "endpoint": ENDPOINT,
        "keys": {"p256dh": KEY, "auth": AUTH},
        "language": "it",
        "app_url": "https://ha.local/app/",
    }
    return base | changes


def test_the_public_key_is_a_p256_point_and_stable(client: TestClient) -> None:
    first = client.get("/api/v1/push/key").json()["public_key"]
    assert len(first) == 87 and first.startswith("B")
    assert client.get("/api/v1/push/key").json()["public_key"] == first


def test_subscribing_creates_then_refreshes(client: TestClient) -> None:
    created = client.post("/api/v1/push/subscriptions", json=body(), headers={"User-Agent": "Fx"})
    assert created.status_code == 201
    out = created.json()
    assert out["events"] == ["blocked", "pairing_lost", "time_warning", "tv_unreachable"]
    assert out["user_agent"] == "Fx" and out["current"] is True and "endpoint" not in out
    again = client.post("/api/v1/push/subscriptions", json=body(events=["blocked"]))
    assert again.status_code == 200 and again.json()["id"] == out["id"]
    assert again.json()["events"] == ["blocked"]
    listed = client.get("/api/v1/push/subscriptions").json()
    assert len(listed) == 1 and listed[0]["current"] is False
    marked = client.get("/api/v1/push/subscriptions", params={"endpoint": ENDPOINT}).json()
    assert marked[0]["current"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"endpoint": "http://push.example.net/x"},
        {"endpoint": "https://"},
        {"keys": {"p256dh": "AAAA", "auth": AUTH}},
        {"keys": {"p256dh": KEY, "auth": "AAAA"}},
        {"keys": {"p256dh": "!!!", "auth": AUTH}},
        {"events": ["redirected"]},
        {"app_url": "javascript:alert(1)"},
    ],
)
def test_invalid_subscriptions_are_rejected(client: TestClient, changes: dict[str, object]) -> None:
    response = client.post("/api/v1/push/subscriptions", json=body(**changes))
    assert response.status_code == 422


def test_events_can_be_changed_and_a_device_removed(client: TestClient) -> None:
    sub_id = client.post("/api/v1/push/subscriptions", json=body()).json()["id"]
    changed = client.patch(f"/api/v1/push/subscriptions/{sub_id}", json={"events": ["blocked"]})
    assert changed.status_code == 200 and changed.json()["events"] == ["blocked"]
    assert client.patch("/api/v1/push/subscriptions/nope", json={"events": []}).status_code == 404
    assert client.delete(f"/api/v1/push/subscriptions/{sub_id}").status_code == 204
    assert client.delete(f"/api/v1/push/subscriptions/{sub_id}").status_code == 404
    assert client.get("/api/v1/push/subscriptions").json() == []


def test_a_test_notification_is_sent_and_a_gone_device_is_dropped(
    client: TestClient, sender: FakeSender
) -> None:
    sub_id = client.post("/api/v1/push/subscriptions", json=body()).json()["id"]
    sent = client.post(f"/api/v1/push/subscriptions/{sub_id}/test")
    assert sent.json() == {"result": "delivered"}
    assert sender.sent[0][0].endpoint == ENDPOINT
    assert sender.sent[0][1]["body"] == "Le notifiche funzionano."
    sender.result = SendResult.GONE
    assert client.post(f"/api/v1/push/subscriptions/{sub_id}/test").json() == {"result": "gone"}
    assert client.get("/api/v1/push/subscriptions").json() == []
    assert client.post("/api/v1/push/subscriptions/nope/test").status_code == 404


def test_an_engine_event_reaches_the_subscribed_device(
    client: TestClient, sender: FakeSender
) -> None:
    tv_id = seed_tv(client)
    client.post("/api/v1/push/subscriptions", json=body())
    app = client.app
    assert client.portal is not None
    client.portal.call(
        app.state.events.publish,  # type: ignore[attr-defined]
        tv_id,
        "pairing_lost",
        {"reason": "x"},
        FakeClock().now(),
    )
    for _ in range(100):
        if sender.sent:
            break
        client.portal.call(asyncio.sleep, 0.02)
    assert len(sender.sent) == 1 and sender.sent[0][1]["title"] == "Living room"


def test_push_needs_a_full_admin(client: TestClient) -> None:
    token = client.post("/api/v1/auth/tokens", json={"name": "t", "scopes": ["admin"]}).json()[
        "token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/push/key", headers=headers).status_code == 403
    assert (
        client.post("/api/v1/push/subscriptions", json=body(), headers=headers).status_code == 403
    )
    client.cookies.clear()
    assert client.get("/api/v1/push/key").status_code == 401
