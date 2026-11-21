from __future__ import annotations

import plistlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography import x509
from fastapi.testclient import TestClient
from support import FakeClock, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.infra import tls


def _running(config: EngineConfig) -> Iterator[TestClient]:
    app = create_app(plugins={}, config=config, clock=FakeClock())
    with TestClient(app) as running:
        yield running


@pytest.fixture
def client(engine_config: EngineConfig) -> Iterator[TestClient]:
    yield from _running(engine_config)


@pytest.fixture
def off_client(tmp_path: Path) -> Iterator[TestClient]:
    yield from _running(EngineConfig(data_dir=tmp_path / "data", tls_mode="off"))


def test_info_announces_the_https_port_when_it_is_active(client: TestClient) -> None:
    assert client.get("/api/v1/info").json()["https_port"] == 8766


def test_info_has_no_https_port_when_off(off_client: TestClient) -> None:
    assert off_client.get("/api/v1/info").json()["https_port"] is None


def test_status_needs_a_full_admin(client: TestClient) -> None:
    assert client.get("/api/v1/tls").status_code in (401, 403)
    sign_in_as_admin(client)
    body = client.get("/api/v1/tls").json()
    assert body["mode"] == "auto" and body["active"] is True and body["https_port"] == 8766
    assert "localhost" in body["names"] and body["error"] is None
    assert body["ca_fingerprint"].count(":") == 31 and body["expires_at"]
    assert any(url.startswith("https://") and url.endswith(":8766") for url in body["urls"])


def test_ca_certificate_is_public_and_matches_the_fingerprint(client: TestClient) -> None:
    resp = client.get("/api/v1/tls/ca.crt")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-x509-ca-cert")
    assert "attachment" in resp.headers["content-disposition"]
    cert = x509.load_pem_x509_certificate(resp.content)
    sign_in_as_admin(client)
    assert client.get("/api/v1/tls").json()["ca_fingerprint"] == tls.fingerprint(cert)


def test_ios_profile_is_public_and_carries_the_same_ca(client: TestClient) -> None:
    resp = client.get("/api/v1/tls/ca.mobileconfig")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-apple-aspen-config")
    profile = plistlib.loads(resp.content)
    der = profile["PayloadContent"][0]["PayloadContent"]
    pem = client.get("/api/v1/tls/ca.crt").content
    assert x509.load_der_x509_certificate(der) == x509.load_pem_x509_certificate(pem)


def test_there_is_no_ca_to_download_when_off(off_client: TestClient) -> None:
    assert off_client.get("/api/v1/tls/ca.crt").status_code == 404
    assert off_client.get("/api/v1/tls/ca.mobileconfig").status_code == 404


def test_rotating_needs_a_full_admin_and_changes_the_ca(client: TestClient) -> None:
    assert client.post("/api/v1/tls/rotate").status_code in (401, 403)
    sign_in_as_admin(client)
    before = client.get("/api/v1/tls").json()["ca_fingerprint"]
    resp = client.post("/api/v1/tls/rotate")
    assert resp.status_code == 200
    assert resp.json()["ca_fingerprint"] != before
    assert client.get("/api/v1/tls").json()["ca_fingerprint"] == resp.json()["ca_fingerprint"]


def test_rotating_is_refused_when_off(off_client: TestClient) -> None:
    sign_in_as_admin(off_client)
    resp = off_client.post("/api/v1/tls/rotate")
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "tls_not_automatic"
    status = off_client.get("/api/v1/tls").json()
    assert status["active"] is False and status["urls"] == []
