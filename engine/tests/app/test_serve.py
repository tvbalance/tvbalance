from __future__ import annotations

import asyncio
import hashlib
import socket
import ssl
from pathlib import Path

import httpx
import pytest

from tvbalance.__main__ import serve
from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.infra import tls


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def _until(check, limit: float = 15.0) -> None:  # type: ignore[no-untyped-def]
    deadline = asyncio.get_running_loop().time() + limit
    while not check():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not reached")
        await asyncio.sleep(0.05)


def _fingerprint_blocking(port: int) -> str:
    pem = ssl.get_server_certificate(("127.0.0.1", port), timeout=5)
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()


async def _served_fingerprint(port: int) -> str:
    """What the HTTPS port presents; asked from a thread because the server shares this loop."""
    for _ in range(100):
        try:
            return await asyncio.to_thread(_fingerprint_blocking, port)
        except OSError:
            await asyncio.sleep(0.1)
    raise AssertionError("HTTPS never answered")


async def _serve_in_background(config: EngineConfig, stop: asyncio.Event):  # type: ignore[no-untyped-def]
    app = create_app(plugins={}, config=config)
    task = asyncio.create_task(serve(config, app=app, stop=stop))
    await _until(lambda: task.done() or getattr(app.state, "tls", None) is not None)
    return app, task


def _config(tmp_path: Path, **extra: str) -> EngineConfig:
    return EngineConfig.from_env(
        {
            "TVBALANCE_HOST": "127.0.0.1",
            "TVBALANCE_PORT": str(_free_port()),
            "TVBALANCE_HTTPS_PORT": str(_free_port()),
            "TVBALANCE_DATA_DIR": str(tmp_path / "data"),
            **extra,
        }
    )


async def _get(url: str, **kwargs):  # type: ignore[no-untyped-def]
    async with httpx.AsyncClient(timeout=5, **kwargs) as client:
        for _ in range(100):
            try:
                return await client.get(url)
            except httpx.TransportError:
                await asyncio.sleep(0.1)
    raise AssertionError(f"{url} never answered")


async def test_serves_http_and_https_with_the_local_ca(tmp_path: Path) -> None:
    config = _config(tmp_path)
    stop = asyncio.Event()
    app, task = await _serve_in_background(config, stop)
    try:
        assert (await _get(f"http://127.0.0.1:{config.port}/api/v1/health")).json() == {
            "status": "ok"
        }
        ca = app.state.tls.ca_certificate()
        context = ssl.create_default_context(cadata=tls.cert_pem(ca).decode())
        secure = await _get(f"https://127.0.0.1:{config.https_port}/api/v1/health", verify=context)
        assert secure.json() == {"status": "ok"}
        with pytest.raises(httpx.ConnectError):
            async with httpx.AsyncClient() as plain:
                await plain.get(f"https://127.0.0.1:{config.https_port}/api/v1/health")
    finally:
        stop.set()
        await asyncio.wait_for(task, 15)


async def test_a_renewed_certificate_is_served_without_a_restart(tmp_path: Path) -> None:
    config = _config(tmp_path)
    stop = asyncio.Event()
    app, task = await _serve_in_background(config, stop)
    try:
        await _get(f"http://127.0.0.1:{config.port}/api/v1/health")
        before = await _served_fingerprint(config.https_port)
        await app.state.tls.rotate()
        assert await _served_fingerprint(config.https_port) != before
    finally:
        stop.set()
        await asyncio.wait_for(task, 15)


async def test_https_off_leaves_the_port_closed(tmp_path: Path) -> None:
    config = _config(tmp_path, TVBALANCE_TLS="off")
    stop = asyncio.Event()
    _app, task = await _serve_in_background(config, stop)
    try:
        await _get(f"http://127.0.0.1:{config.port}/api/v1/health")
        with pytest.raises(OSError):
            await asyncio.to_thread(socket.create_connection, ("127.0.0.1", config.https_port), 1)
    finally:
        stop.set()
        await asyncio.wait_for(task, 15)


async def test_a_busy_https_port_does_not_stop_http(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", config.https_port))
    blocker.listen(1)
    stop = asyncio.Event()
    _app, task = await _serve_in_background(config, stop)
    try:
        assert (await _get(f"http://127.0.0.1:{config.port}/api/v1/health")).status_code == 200
        await asyncio.sleep(0.5)
        assert not task.done()
    finally:
        stop.set()
        await asyncio.wait_for(task, 15)
        blocker.close()
