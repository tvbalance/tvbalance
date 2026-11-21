import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from support import (
    FAST,
    FakeClock,
    ScriptedTV,
    plugin_for,
    seed_tv,
    sign_in_as_admin,
    wait_connected,
    watching,
)

from tvbalance.api.app import create_app
from tvbalance.app import icons
from tvbalance.config import EngineConfig
from tvbalance.sdk.types import AppInfo

PNG = b"\x89PNG\r\n\x1a\nfake"


class TvHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/ok.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(PNG)
        elif self.path == "/page.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html></html>")
        elif self.path == "/huge.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(b"x" * (icons.MAX_BYTES + 1))
        elif self.path == "/redirect.png":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.2:1/elsewhere.png")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def tv_server() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), TvHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def client(engine_config: EngineConfig, tv_server: str) -> Iterator[TestClient]:
    tv = ScriptedTV(
        observation=watching(),
        apps=[
            AppInfo("ok", "Ok", f"{tv_server}/ok.png"),
            AppInfo("html", "Html", f"{tv_server}/page.html"),
            AppInfo("huge", "Huge", f"{tv_server}/huge.png"),
            AppInfo("gone", "Gone", f"{tv_server}/missing.png"),
            AppInfo("redirect", "Redirect", f"{tv_server}/redirect.png"),
            AppInfo("foreign", "Foreign", "http://203.0.113.50/icon.png"),
            AppInfo("plain", "Plain"),
        ],
    )
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


@pytest.fixture
def tv_id(client: TestClient) -> str:
    tv_id = seed_tv(client, host="127.0.0.1")
    wait_connected(client, tv_id)
    return tv_id


def test_the_icon_is_served_from_the_engine(client: TestClient, tv_id: str) -> None:
    response = client.get(f"/api/v1/tvs/{tv_id}/apps/ok/icon")
    assert response.status_code == 200 and response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert "max-age" in response.headers["cache-control"]


@pytest.mark.parametrize("app_id", ["plain", "unknown"])
def test_apps_without_an_icon_are_not_found(client: TestClient, tv_id: str, app_id: str) -> None:
    assert client.get(f"/api/v1/tvs/{tv_id}/apps/{app_id}/icon").status_code == 404


@pytest.mark.parametrize("app_id", ["html", "huge", "gone", "redirect", "foreign"])
def test_icons_that_are_not_safe_images_are_refused(
    client: TestClient, tv_id: str, app_id: str
) -> None:
    response = client.get(f"/api/v1/tvs/{tv_id}/apps/{app_id}/icon")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "icon_unavailable"


def test_icons_need_the_read_scope(client: TestClient, tv_id: str) -> None:
    client.cookies.clear()
    assert client.get(f"/api/v1/tvs/{tv_id}/apps/ok/icon").status_code == 401
