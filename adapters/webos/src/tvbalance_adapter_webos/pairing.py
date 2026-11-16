"""Pairing: connect without a key, so the TV asks its owner to accept the new device."""

from __future__ import annotations

import asyncio
import contextlib

import aiohttp
from aiowebostv import WebOsTvPairError
from aiowebostv.exceptions import WebOsTvError

from tvbalance.sdk.types import PairingState
from tvbalance_adapter_webos._client import make_client

# The library gives up on a prompt after 10 s; asking again keeps it on screen long enough
# for a person to find the remote.
MAX_ATTEMPTS = 6
_POLL_WAIT = 1.0
_RETRY = object()


class WebOsPairing:
    def __init__(self, host: str) -> None:
        self._host = host
        self._state = PairingState.IDLE
        self._key: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> PairingState:
        if self._task is None:
            self._state = PairingState.WAITING_FOR_USER
            self._task = asyncio.create_task(self._run())
        return self._state

    async def poll(self) -> PairingState:
        if self._task is not None and self._state is PairingState.WAITING_FOR_USER:
            await asyncio.wait({self._task}, timeout=_POLL_WAIT)
        return self._state

    def credentials(self) -> dict[str, str]:
        return {"client_key": self._key} if self._key else {}

    async def cancel(self) -> None:
        """Abandon a pending attempt (the user left the pairing screen)."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._state is PairingState.WAITING_FOR_USER:
            self._state = PairingState.FAILED

    async def _run(self) -> None:
        outcome = PairingState.FAILED
        try:
            for _ in range(MAX_ATTEMPTS):
                key = await self._attempt()
                if key is not _RETRY:
                    if key:
                        self._key = str(key)
                        outcome = PairingState.COMPLETED
                    break
        finally:
            self._state = outcome

    async def _attempt(self) -> str | object | None:
        """One connection without a key: the key, ``None`` on failure or ``_RETRY`` on timeout."""
        client, session = make_client(self._host, None)
        try:
            await client.connect()
            return client.client_key
        except TimeoutError:
            return _RETRY
        except (WebOsTvPairError, WebOsTvError, OSError, aiohttp.ClientError):
            return None
        finally:
            with contextlib.suppress(WebOsTvError, OSError, aiohttp.ClientError):
                await client.disconnect()
            if session is not None:
                await session.close()
