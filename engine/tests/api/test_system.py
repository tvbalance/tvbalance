import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tvbalance import __version__
from tvbalance.api.app import create_app
from tvbalance.sdk.fake import PLUGIN
from tvbalance.sdk.types import Capability

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(plugins={"fake": PLUGIN}))


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_info_lists_adapters_with_capabilities(client: TestClient) -> None:
    body = client.get("/api/v1/info").json()
    assert body["version"] == __version__
    assert body["api_version"] == "1"
    (adapter,) = body["adapters"]
    assert adapter["id"] == "fake"
    assert adapter["maturity"] == "experimental"
    assert set(adapter["capabilities"]) == {c.value for c in Capability}


def test_openapi_document_is_up_to_date() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_openapi", ROOT / "scripts/export_openapi.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = (ROOT / "openapi.json").read_text(encoding="utf-8")
    assert json.loads(committed) == json.loads(module.render()), (
        "openapi.json is stale: run `uv run python engine/scripts/export_openapi.py`"
    )


def test_web_ui_is_served_after_the_api_routes(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>ui</h1>", encoding="utf-8")
    client = TestClient(create_app(plugins={}, web_dir=tmp_path))
    assert client.get("/").text == "<h1>ui</h1>"
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_missing_web_dir_leaves_only_the_api(tmp_path: Path) -> None:
    client = TestClient(create_app(plugins={}, web_dir=tmp_path / "absent"))
    assert client.get("/").status_code == 404
