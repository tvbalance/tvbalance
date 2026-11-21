from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path

import pytest
from cryptography import x509
from support import FakeClock

from tvbalance.app import tls as tls_app
from tvbalance.app.tls import CA_CERT_SECRET, TlsManager
from tvbalance.config import EngineConfig
from tvbalance.infra import tls


class MemorySecrets:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


def _names(*names: str):  # type: ignore[no-untyped-def]
    current = list(names)

    async def source() -> list[str]:
        return list(current)

    source.names = current  # type: ignore[attr-defined]
    return source


def _manager(
    tmp_path: Path, secrets: MemorySecrets, clock: FakeClock, names, **env: str
) -> TlsManager:  # type: ignore[no-untyped-def]
    config = EngineConfig.from_env({"TVBALANCE_DATA_DIR": str(tmp_path), **env})
    return TlsManager(secrets, config, clock, names, check_interval=0.01)


async def test_auto_mode_creates_the_ca_and_a_server_certificate(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    manager = _manager(tmp_path, secrets, clock, _names("localhost", "10.1.2.3", "example.com"))
    await manager.prepare()
    status = manager.status()
    assert status.active and status.mode == "auto" and status.https_port == 8766
    assert status.names == ["localhost", "10.1.2.3"] and status.skipped_names == ["example.com"]
    assert status.ca_fingerprint and status.expires_at is not None
    assert manager.certfile and manager.certfile.exists()
    assert manager.keyfile and manager.keyfile.exists()
    cert = x509.load_pem_x509_certificate(manager.certfile.read_bytes())
    ca = manager.ca_certificate()
    assert ca is not None and cert.issuer == ca.subject
    if os.name == "posix":
        assert stat.S_IMODE(manager.keyfile.stat().st_mode) == 0o600


async def test_the_ca_is_kept_across_restarts(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    first = _manager(tmp_path, secrets, clock, _names("localhost"))
    await first.prepare()
    second = _manager(tmp_path, secrets, clock, _names("localhost"))
    await second.prepare()
    assert second.status().ca_fingerprint == first.status().ca_fingerprint
    assert not await second.renew_if_needed()


async def test_an_unusable_stored_ca_is_replaced(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    first = _manager(tmp_path, secrets, clock, _names("localhost"))
    await first.prepare()
    secrets.values[CA_CERT_SECRET] = "garbage"
    second = _manager(tmp_path, secrets, clock, _names("localhost"))
    await second.prepare()
    assert second.status().active
    assert second.status().ca_fingerprint != first.status().ca_fingerprint


async def test_renewal_happens_near_expiry_and_notifies(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    manager = _manager(tmp_path, secrets, clock, _names("localhost"))
    await manager.prepare()
    calls: list[int] = []
    manager.on_renew(lambda: calls.append(1))
    before = manager.status().expires_at
    clock.advance(days=100)
    assert not await manager.renew_if_needed() and not calls
    clock.advance(days=280)
    assert await manager.renew_if_needed()
    assert calls == [1]
    assert manager.status().expires_at != before


async def test_new_addresses_trigger_a_new_certificate(tmp_path: Path) -> None:
    secrets, clock, names = MemorySecrets(), FakeClock(), _names("localhost")
    manager = _manager(tmp_path, secrets, clock, names)
    await manager.prepare()
    names.names.append("10.9.8.7")  # type: ignore[attr-defined]
    assert await manager.renew_if_needed()
    assert "10.9.8.7" in manager.status().names


async def test_rotate_replaces_the_ca(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    manager = _manager(tmp_path, secrets, clock, _names("localhost"))
    await manager.prepare()
    old = manager.status().ca_fingerprint
    calls: list[int] = []
    manager.on_renew(lambda: calls.append(1))
    await manager.rotate()
    assert manager.status().ca_fingerprint != old and calls == [1]


async def test_a_failing_listener_does_not_stop_renewal(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    manager = _manager(tmp_path, secrets, clock, _names("localhost"))
    await manager.prepare()

    def boom() -> None:
        raise RuntimeError("nope")

    manager.on_renew(boom)
    await manager.rotate()
    assert manager.status().active


async def test_off_mode_does_nothing(tmp_path: Path) -> None:
    manager = _manager(
        tmp_path, MemorySecrets(), FakeClock(), _names("localhost"), TVBALANCE_TLS="off"
    )
    await manager.prepare()
    status = manager.status()
    assert not status.active and status.mode == "off" and status.ca_fingerprint is None
    assert manager.certfile is None
    with pytest.raises(tls.TlsError):
        await manager.rotate()


def _custom_files(tmp_path: Path, clock: FakeClock) -> tuple[Path, Path]:
    ca = tls.create_ca(clock.now())
    cert, key = tls.issue_server_cert(ca, ["tv.local"], clock.now())
    certfile, keyfile = tmp_path / "own.crt", tmp_path / "own.key"
    certfile.write_bytes(tls.cert_pem(cert))
    keyfile.write_bytes(tls.key_pem(key))
    return certfile, keyfile


async def test_custom_mode_uses_the_users_files(tmp_path: Path) -> None:
    clock = FakeClock()
    certfile, keyfile = _custom_files(tmp_path, clock)
    manager = _manager(
        tmp_path,
        MemorySecrets(),
        clock,
        _names(),
        TVBALANCE_TLS_CERTFILE=str(certfile),
        TVBALANCE_TLS_KEYFILE=str(keyfile),
    )
    await manager.prepare()
    status = manager.status()
    assert status.active and status.mode == "custom" and status.names == ["tv.local"]
    assert status.ca_fingerprint is None and manager.ca_certificate() is None
    assert (manager.certfile, manager.keyfile) == (certfile, keyfile)
    with pytest.raises(tls.TlsError):
        await manager.rotate()


async def test_custom_mode_notices_replaced_files(tmp_path: Path) -> None:
    clock = FakeClock()
    certfile, keyfile = _custom_files(tmp_path, clock)
    manager = _manager(
        tmp_path,
        MemorySecrets(),
        clock,
        _names(),
        TVBALANCE_TLS_CERTFILE=str(certfile),
        TVBALANCE_TLS_KEYFILE=str(keyfile),
    )
    await manager.prepare()
    calls: list[int] = []
    manager.on_renew(lambda: calls.append(1))
    assert not await manager.renew_if_needed()
    other = tmp_path / "other"
    other.mkdir()
    new_cert, new_key = _custom_files(other, clock)
    certfile.write_bytes(new_cert.read_bytes())
    keyfile.write_bytes(new_key.read_bytes())
    os.utime(certfile, (1, 1))
    assert await manager.renew_if_needed()
    assert calls == [1]


async def test_a_broken_custom_certificate_disables_https_without_raising(tmp_path: Path) -> None:
    (tmp_path / "bad.crt").write_text("nope", encoding="utf-8")
    (tmp_path / "bad.key").write_text("nope", encoding="utf-8")
    manager = _manager(
        tmp_path,
        MemorySecrets(),
        FakeClock(),
        _names(),
        TVBALANCE_TLS_CERTFILE=str(tmp_path / "bad.crt"),
        TVBALANCE_TLS_KEYFILE=str(tmp_path / "bad.key"),
    )
    await manager.prepare()
    status = manager.status()
    assert not status.active and status.error and "certificate" in status.error


async def test_no_usable_name_disables_https(tmp_path: Path) -> None:
    manager = _manager(tmp_path, MemorySecrets(), FakeClock(), _names("example.com"))
    await manager.prepare()
    assert not manager.status().active and manager.status().error


async def test_the_background_task_renews_and_stops(tmp_path: Path) -> None:
    secrets, clock = MemorySecrets(), FakeClock()
    manager = _manager(tmp_path, secrets, clock, _names("localhost"))
    await manager.prepare()
    calls: list[int] = []
    manager.on_renew(lambda: calls.append(1))
    clock.advance(days=380)
    manager.start()
    for _ in range(100):
        if calls:
            break
        await asyncio.sleep(0.02)
    await manager.stop()
    assert calls


async def test_detected_names_include_local_addresses_and_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tls_app, "_primary_ipv4", lambda: "10.4.5.6")
    monkeypatch.setattr(tls_app.socket, "gethostname", lambda: "Box")
    config = EngineConfig.from_env({"TVBALANCE_TLS_NAMES": "tv.lan"})
    names = await tls_app.detect_names(config)()
    assert {"localhost", "127.0.0.1", "::1", "tv.lan", "box.local", "10.4.5.6"} <= set(names)


async def test_the_supervisor_adds_the_host_name_and_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tls_app, "_primary_ipv4", lambda: None)

    def fake(config: EngineConfig, path: str) -> dict[str, object]:
        if path == "/host/info":
            return {"hostname": "homeassistant"}
        return {"interfaces": [{"ipv4": {"address": ["172.16.5.9/24"]}}, {"ipv4": None}]}

    monkeypatch.setattr(tls_app, "_supervisor_data", fake)
    config = EngineConfig.from_env({"SUPERVISOR_TOKEN": "t"})
    names = await tls_app.detect_names(config)()
    assert {"homeassistant", "homeassistant.local", "172.16.5.9"} <= set(names)


async def test_an_unreachable_supervisor_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tls_app, "_primary_ipv4", lambda: None)

    def fail(config: EngineConfig, path: str) -> dict[str, object]:
        raise OSError("no route")

    monkeypatch.setattr(tls_app, "_supervisor_data", fail)
    config = EngineConfig.from_env({"SUPERVISOR_TOKEN": "t"})
    assert "localhost" in await tls_app.detect_names(config)()
