import json
import threading
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from support import FakeClock

from tvbalance.app.auth import AuthService
from tvbalance.app.ha_discovery import DiscoveryError, HomeAssistantDiscovery
from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage

SUPERVISOR_TOKEN = "supervisor-secret"


class FakeSupervisor:
    """A local HTTP server that answers like the Home Assistant Supervisor."""

    def __init__(self) -> None:
        self.addon: dict[str, Any] = {"ip_address": "172.30.33.5", "hostname": "abc-tvbalance"}
        self.requests: list[tuple[str, str, str | None, Any]] = []
        self.fail_next = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                outer.requests.append(
                    (self.command, self.path, self.headers.get("Authorization"), body)
                )
                if outer.fail_next:
                    outer.fail_next -= 1
                    self.send_response(503)
                    self.end_headers()
                    return
                if self.path == "/addons/self/info":
                    payload: dict[str, Any] = {"result": "ok", "data": outer.addon}
                else:
                    payload = {"result": "ok", "data": {"uuid": "d1"}}
                raw = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = do_POST = _handle

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    @property
    def posts(self) -> list[Any]:
        return [body for method, _, _, body in self.requests if method == "POST"]


@pytest.fixture
def supervisor() -> Iterator[FakeSupervisor]:
    fake = FakeSupervisor()
    fake.start()
    yield fake
    fake.stop()


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FakeClock())
    yield store
    await store.close()


@pytest.fixture
def auth(storage: Storage) -> AuthService:
    return AuthService(storage.auth, FakeClock())


def make(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage, **overrides: Any
) -> HomeAssistantDiscovery:
    config = EngineConfig(
        port=8765, supervisor_token=SUPERVISOR_TOKEN, supervisor_url=supervisor.url
    )
    return HomeAssistantDiscovery(
        auth, storage.secrets, config, initial_delay=0.01, max_delay=0.02, **overrides
    )


async def test_publishes_the_address_and_a_token_that_works(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    await make(supervisor, auth, storage).publish()

    (body,) = supervisor.posts
    assert body["service"] == "tvbalance"
    assert body["config"]["host"] == "172.30.33.5"
    assert body["config"]["port"] == 8765
    principal = await auth.authenticate_token(body["config"]["token"])
    assert principal is not None
    assert principal.scopes == frozenset({"read", "control"})
    assert principal.name == "Home Assistant (Add-on)"
    assert all(
        auth_header == f"Bearer {SUPERVISOR_TOKEN}" for _, _, auth_header, _ in supervisor.requests
    )


async def test_falls_back_to_the_hostname_without_an_ip_address(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    supervisor.addon = {"ip_address": None, "hostname": "abc-tvbalance"}
    await make(supervisor, auth, storage).publish()
    assert supervisor.posts[0]["config"]["host"] == "abc-tvbalance"


async def test_the_same_token_is_reused_across_runs(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    await make(supervisor, auth, storage).publish()
    await make(supervisor, auth, storage).publish()
    first, second = supervisor.posts
    assert first["config"]["token"] == second["config"]["token"]
    assert len(await auth.list_tokens()) == 1


async def test_a_revoked_token_is_replaced(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    await make(supervisor, auth, storage).publish()
    (record,) = await auth.list_tokens()
    await auth.revoke_token(record.id)

    await make(supervisor, auth, storage).publish()

    first, second = supervisor.posts
    assert first["config"]["token"] != second["config"]["token"]
    assert await auth.authenticate_token(second["config"]["token"]) is not None


async def test_the_token_is_not_kept_in_clear_text(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage, tmp_path: Path
) -> None:
    await make(supervisor, auth, storage).publish()
    token = supervisor.posts[0]["config"]["token"]
    await storage.close()
    assert token.encode() not in (tmp_path / "data" / "tvbalance.db").read_bytes()


async def test_a_supervisor_error_is_reported(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    supervisor.fail_next = 1
    with pytest.raises(DiscoveryError):
        await make(supervisor, auth, storage).publish()


async def test_an_unreachable_supervisor_is_reported(auth: AuthService, storage: Storage) -> None:
    config = EngineConfig(supervisor_token="t", supervisor_url="http://127.0.0.1:1")
    with pytest.raises(DiscoveryError):
        await HomeAssistantDiscovery(auth, storage.secrets, config).publish()


async def test_run_retries_until_the_supervisor_answers(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    supervisor.fail_next = 3
    await make(supervisor, auth, storage).run()
    assert len(supervisor.posts) == 1


async def test_start_and_stop_run_in_the_background(
    supervisor: FakeSupervisor, auth: AuthService, storage: Storage
) -> None:
    discovery = make(supervisor, auth, storage)
    discovery.start()
    await discovery.wait()
    await discovery.stop()
    assert len(supervisor.posts) == 1


async def test_stop_cancels_a_run_that_cannot_reach_the_supervisor(
    auth: AuthService, storage: Storage
) -> None:
    config = EngineConfig(supervisor_token="t", supervisor_url="http://127.0.0.1:1")
    discovery = HomeAssistantDiscovery(
        auth, storage.secrets, config, initial_delay=0.01, max_delay=0.02
    )
    discovery.start()
    await discovery.stop()
