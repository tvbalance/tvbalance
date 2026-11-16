"""Typed, dependency-light client. It must not import the engine (separate release cycle)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

import aiohttp

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


class TVBalanceError(Exception):
    """The Engine answered with an error."""


class TVBalanceConnectionError(TVBalanceError):
    """The Engine could not be reached."""


@dataclass(frozen=True, slots=True)
class AdapterSummary:
    id: str
    brand: str
    display_name: str
    maturity: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EngineInfo:
    version: str
    api_version: str
    adapters: tuple[AdapterSummary, ...]


class TVBalanceClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session is not None and self._owns_session:
            await self._session.close()
            self._session = None

    async def _get(self, path: str) -> dict[str, Any]:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with self._session.get(f"{self._base_url}{path}", headers=headers) as resp:
                if resp.status >= 400:
                    raise TVBalanceError(f"{path}: HTTP {resp.status}")
                data: dict[str, Any] = await resp.json()
                return data
        except aiohttp.ClientConnectionError as ex:
            raise TVBalanceConnectionError(f"cannot reach {self._base_url}: {ex}") from ex
        except TimeoutError as ex:
            raise TVBalanceConnectionError(f"timeout reaching {self._base_url}") from ex

    async def health(self) -> bool:
        return (await self._get("/api/v1/health")).get("status") == "ok"

    async def info(self) -> EngineInfo:
        raw = await self._get("/api/v1/info")
        return EngineInfo(
            version=raw["version"],
            api_version=raw["api_version"],
            adapters=tuple(
                AdapterSummary(
                    id=a["id"],
                    brand=a["brand"],
                    display_name=a["display_name"],
                    maturity=a["maturity"],
                    capabilities=tuple(a["capabilities"]),
                )
                for a in raw["adapters"]
            ),
        )
