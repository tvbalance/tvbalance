"""Tell Home Assistant where this Engine is, so the integration needs no typed URL or token.

Inside an Add-on the Supervisor accepts a discovery message; Home Assistant then offers the
TVBalance integration with the address and an API token filled in.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from tvbalance.app.auth import AuthService
from tvbalance.config import EngineConfig
from tvbalance.ports.storage import SecretSettingsStore

log = logging.getLogger(__name__)

SERVICE = "tvbalance"
TOKEN_NAME = "Home Assistant (Add-on)"
TOKEN_SCOPES = frozenset({"read", "control"})
TOKEN_KEY = "ha_discovery_token"
REQUEST_TIMEOUT = 10.0


class DiscoveryError(Exception):
    """The Supervisor could not be reached or refused the request."""


class HomeAssistantDiscovery:
    def __init__(
        self,
        auth: AuthService,
        secrets: SecretSettingsStore,
        config: EngineConfig,
        *,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        self._auth, self._secrets, self._config = auth, secrets, config
        self._initial_delay, self._max_delay = initial_delay, max_delay
        self._task: asyncio.Task[None] | None = None

    async def ensure_token(self) -> str:
        """The API token handed to Home Assistant: kept across restarts, replaced once revoked."""
        stored = await self._secrets.get(TOKEN_KEY)
        if stored and await self._auth.authenticate_token(stored) is not None:
            return stored
        issued = await self._auth.create_token(TOKEN_NAME, TOKEN_SCOPES)
        await self._secrets.set(TOKEN_KEY, issued.token)
        return issued.token

    async def publish(self) -> None:
        info = await self._request("GET", "/addons/self/info")
        host = info.get("ip_address") or info.get("hostname")
        if not host:
            raise DiscoveryError("the Supervisor did not say where this Add-on can be reached")
        token = await self.ensure_token()
        await self._request(
            "POST",
            "/discovery",
            {
                "service": SERVICE,
                "config": {"host": host, "port": self._config.port, "token": token},
            },
        )
        log.info("announced the Engine to Home Assistant at %s:%s", host, self._config.port)

    async def run(self) -> None:
        """Publish, retrying with growing pauses until the Supervisor accepts."""
        delay = self._initial_delay
        while True:
            try:
                await self.publish()
                return
            except DiscoveryError as ex:
                log.warning("Home Assistant discovery failed (%s); retrying in %.0f s", ex, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, self._max_delay)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run(), name="ha-discovery")

    async def wait(self) -> None:
        if self._task is not None:
            await self._task

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        return await asyncio.to_thread(self._request_sync, method, path, body)

    def _request_sync(self, method: str, path: str, body: dict[str, Any] | None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self._config.supervisor_url.rstrip("/") + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._config.supervisor_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as ex:
            raise DiscoveryError(f"{method} {path}: {ex}") from ex
        if not isinstance(payload, dict) or payload.get("result") != "ok":
            raise DiscoveryError(f"{method} {path}: unexpected answer")
        return payload.get("data") or {}
