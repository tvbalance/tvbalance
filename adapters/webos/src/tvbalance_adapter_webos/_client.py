"""Construction of the aiowebostv client, with a hook that lets tests reach a simulated TV."""

from __future__ import annotations

from typing import Any, cast

import aiohttp
from aiowebostv import WebOsClient

# host -> local simulator port. The library always dials :3000/:3001, so tests redirect it.
SIMULATED_PORTS: dict[str, int] = {}


class RedirectingSession:
    """Delegates to a real session but sends every websocket to the simulator."""

    def __init__(self, port: int) -> None:
        self._session = aiohttp.ClientSession()
        self._port = port

    def ws_connect(self, uri: str, **kwargs: Any) -> Any:
        path = uri.split("://", 1)[1].partition("/")[2]
        return self._session.ws_connect(f"ws://127.0.0.1:{self._port}/{path}", **kwargs)

    async def close(self) -> None:
        await self._session.close()


def make_client(host: str, client_key: str | None) -> tuple[WebOsClient, RedirectingSession | None]:
    """A client for ``host`` plus the session to close afterwards (``None`` for a real TV)."""
    port = SIMULATED_PORTS.get(host)
    if port is None:
        return WebOsClient(host, client_key=client_key), None
    session = RedirectingSession(port)
    client = WebOsClient(
        host, client_key=client_key, client_session=cast("aiohttp.ClientSession", session)
    )
    return client, session
