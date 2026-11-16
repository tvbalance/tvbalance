import asyncio
import socket
from collections.abc import AsyncIterator

import pytest
import uvicorn

from tvbalance.api.app import create_app
from tvbalance.sdk.fake import PLUGIN


@pytest.fixture
async def engine_url() -> AsyncIterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(
        create_app(plugins={"fake": PLUGIN}), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:  # noqa: ASYNC110 - polling uvicorn startup flag
        await asyncio.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    await task
