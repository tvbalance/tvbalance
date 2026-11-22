import asyncio
import socket
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import aiohttp
import pytest
import uvicorn
from fastapi import FastAPI

from tvbalance.__main__ import serve
from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.sdk.fake import PLUGIN


@pytest.fixture
def engine_app(tmp_path: Path) -> FastAPI:
    return create_app(
        plugins={"fake": PLUGIN},
        include_testing=True,
        config=EngineConfig(data_dir=tmp_path / "data"),
    )


@pytest.fixture
async def engine_url(engine_app: FastAPI) -> AsyncIterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(
        engine_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:  # noqa: ASYNC110 - polling uvicorn startup flag
        await asyncio.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    await task


@pytest.fixture
async def mint_token(engine_url: str) -> AsyncIterator[Callable[[list[str]], Awaitable[str]]]:
    """Set the admin account up on a fresh engine; the result mints API tokens with given scopes."""
    jar = aiohttp.CookieJar(unsafe=True)  # the engine listens on an IP address
    async with aiohttp.ClientSession(cookie_jar=jar) as http:
        async with http.post(
            f"{engine_url}/api/v1/auth/setup", json={"password": "correct horse battery"}
        ) as resp:
            assert resp.status == 201
            csrf = (await resp.json())["csrf_token"]

        async def mint(scopes: list[str]) -> str:
            async with http.post(
                f"{engine_url}/api/v1/auth/tokens",
                json={"name": "client tests", "scopes": scopes},
                headers={"X-TVBalance-CSRF": csrf},
            ) as made:
                assert made.status == 201
                return str((await made.json())["token"])

        yield mint


@pytest.fixture
async def engine_token(mint_token: Callable[[list[str]], Awaitable[str]]) -> str:
    return await mint_token(["read", "control"])


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
async def https_url(tmp_path: Path) -> AsyncIterator[str]:
    """An engine serving HTTPS with its own local CA, as a household would run it."""
    config = EngineConfig(
        data_dir=tmp_path / "tls-data",
        host="127.0.0.1",
        port=_free_port(),
        https_port=_free_port(),
    )
    stop = asyncio.Event()
    task = asyncio.create_task(serve(config, stop=stop))
    async with aiohttp.ClientSession() as probe:
        for _ in range(200):
            try:
                async with probe.get(
                    f"https://127.0.0.1:{config.https_port}/api/v1/health", ssl=False
                ):
                    break
            except aiohttp.ClientConnectionError:
                await asyncio.sleep(0.05)
        else:
            raise AssertionError("HTTPS never answered")
    yield f"https://127.0.0.1:{config.https_port}"
    stop.set()
    await task
