"""Typed, dependency-light client. It must not import the engine (separate release cycle)."""

from __future__ import annotations

import hashlib
import ssl
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Self

import aiohttp

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)
WS_UNAUTHENTICATED = 4401
WS_FORBIDDEN = 4403


class TVBalanceError(Exception):
    """The Engine answered with an error."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code  # the Engine's stable error code, e.g. "not_found"


class TVBalanceConnectionError(TVBalanceError):
    """The Engine could not be reached."""


class CertificateError(TVBalanceError):
    """The Engine's HTTPS certificate is not the one that was trusted (unknown or changed CA)."""


class AuthenticationError(TVBalanceError):
    """The Engine refused the credentials (401) or the token lacks the needed scope (403)."""


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


@dataclass(frozen=True, slots=True)
class Decision:
    kind: str  # "allow", "warn" or "block"
    reason: str | None  # why it is blocked
    minutes_left: int | None  # how long until a limit, when warning
    limit: str | None = None  # what a warning is about, e.g. "daily_budget"


@dataclass(frozen=True, slots=True)
class ActiveProfile:
    """A rule set switched on for the household, by hand, by the calendar or by an automation."""

    policy_id: int
    name: str
    until: datetime
    source: str  # "manual", "automation" or "calendar"


@dataclass(frozen=True, slots=True)
class TvStatus:
    connected: bool
    pairing_required: bool
    power: str | None
    foreground_app: str | None
    decision: Decision | None
    watched_seconds: int
    remaining_seconds: int | None  # None: no daily budget
    input_id: str | None = None
    channel_id: str | None = None
    program_title: str | None = None
    active_profile: ActiveProfile | None = None


@dataclass(frozen=True, slots=True)
class Caller:
    kind: str  # "admin", "pin", "token" or "ingress"
    scopes: tuple[str, ...]  # "read", "control", "admin"


@dataclass(frozen=True, slots=True)
class Tv:
    id: str
    name: str
    adapter_id: str
    enabled: bool
    policy_id: int | None
    needs_pairing: bool
    status: TvStatus | None  # None while the Engine is not watching this TV


@dataclass(frozen=True, slots=True)
class Override:
    allow: bool
    until: datetime


@dataclass(frozen=True, slots=True)
class Event:
    type: str
    tv_id: str | None
    at: datetime | None
    payload: dict[str, Any]


def ca_fingerprint(pem: str) -> str:
    """The SHA-256 fingerprint of a PEM certificate, as ``AA:BB:...`` like the Engine shows it."""
    digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def ssl_context_for(pem: str) -> ssl.SSLContext:
    """A client context that trusts only the given CA (the Engine's local one)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # no system store: nothing but the CA counts
    context.load_verify_locations(cadata=pem)
    return context


async def fetch_ca_certificate(base_url: str, session: aiohttp.ClientSession | None = None) -> str:
    """Download the Engine's CA unverified; the user confirms its fingerprint."""
    url = f"{base_url.rstrip('/')}/api/v1/tls/ca.crt"
    owned = session is None
    http = session or aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
    try:
        async with http.get(url, ssl=False) as resp:
            if resp.status >= 400:
                raise await TVBalanceClient._failure("/api/v1/tls/ca.crt", resp)
            return await resp.text()
    except aiohttp.ClientConnectionError as ex:
        raise TVBalanceConnectionError(f"cannot reach {base_url}: {ex}") from ex
    finally:
        if owned:
            await http.close()


def _profile(raw: dict[str, Any] | None) -> ActiveProfile | None:
    if raw is None:
        return None
    return ActiveProfile(
        policy_id=raw["policy_id"],
        name=raw["name"],
        until=datetime.fromisoformat(raw["until"]),
        source=raw["source"],
    )


def _status(raw: dict[str, Any] | None) -> TvStatus | None:
    if raw is None:
        return None
    decision = raw["decision"]
    return TvStatus(
        connected=raw["connected"],
        pairing_required=raw["pairing_required"],
        power=raw["power"],
        foreground_app=raw["foreground_app"],
        decision=None
        if decision is None
        else Decision(
            decision["kind"],
            decision["reason"],
            decision["minutes_left"],
            decision.get("limit"),
        ),
        watched_seconds=raw["watched_seconds"],
        remaining_seconds=raw["remaining_seconds"],
        input_id=raw.get("input_id"),
        channel_id=raw.get("channel_id"),
        program_title=raw.get("program_title"),
        active_profile=_profile(raw.get("active_profile")),
    )


def parse_status(raw: dict[str, Any]) -> TvStatus:
    """A TV's status as the Engine sends it, in the API and in ``status`` events."""
    status = _status(raw)
    assert status is not None
    return status


def _tv(raw: dict[str, Any]) -> Tv:
    return Tv(
        id=raw["id"],
        name=raw["name"],
        adapter_id=raw["adapter_id"],
        enabled=raw["enabled"],
        policy_id=raw["policy_id"],
        needs_pairing=raw["needs_pairing"],
        status=_status(raw["status"]),
    )


def _override(raw: dict[str, Any]) -> Override:
    return Override(allow=raw["allow"], until=datetime.fromisoformat(raw["until"]))


class TVBalanceClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        session: aiohttp.ClientSession | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session = session
        self._owns_session = session is None
        self._tls: dict[str, Any] = {} if ssl_context is None else {"ssl": ssl_context}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session is not None and self._owns_session:
            await self._session.close()
            self._session = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _http(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
        return self._session

    @staticmethod
    async def _failure(path: str, resp: aiohttp.ClientResponse) -> TVBalanceError:
        code: str | None = None
        message = HTTPStatus(resp.status).phrase
        try:
            error = (await resp.json())["error"]
            code, message = error["code"], error["message"]
        except (aiohttp.ContentTypeError, ValueError, KeyError, TypeError):
            pass  # not the Engine's envelope: keep the HTTP reason
        text = f"{path}: {message} (HTTP {resp.status})"
        kind = AuthenticationError if resp.status in (401, 403) else TVBalanceError
        return kind(text, status=resp.status, code=code)

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        try:
            async with self._http().request(
                method, f"{self._base_url}{path}", json=body, headers=self._headers(), **self._tls
            ) as resp:
                if resp.status >= 400:
                    raise await self._failure(path, resp)
                return None if resp.status == 204 else await resp.json()
        except aiohttp.ClientConnectorCertificateError as ex:
            raise CertificateError(f"{self._base_url}: {ex}") from ex
        except aiohttp.ClientConnectionError as ex:
            raise TVBalanceConnectionError(f"cannot reach {self._base_url}: {ex}") from ex
        except TimeoutError as ex:
            raise TVBalanceConnectionError(f"timeout reaching {self._base_url}") from ex

    async def health(self) -> bool:
        return bool((await self._request("GET", "/api/v1/health"))["status"] == "ok")

    async def info(self) -> EngineInfo:
        raw = await self._request("GET", "/api/v1/info")
        return EngineInfo(version=raw["version"], api_version=raw["api_version"])

    async def adapters(self) -> list[AdapterSummary]:
        return [
            AdapterSummary(
                id=a["id"],
                brand=a["brand"],
                display_name=a["display_name"],
                maturity=a["maturity"],
                capabilities=tuple(a["capabilities"]),
            )
            for a in await self._request("GET", "/api/v1/adapters")
        ]

    async def tvs(self) -> list[Tv]:
        return [_tv(raw) for raw in await self._request("GET", "/api/v1/tvs")]

    async def tv(self, tv_id: str) -> Tv:
        return _tv(await self._request("GET", f"/api/v1/tvs/{tv_id}"))

    async def update_tv(
        self, tv_id: str, *, enabled: bool | None = None, name: str | None = None
    ) -> Tv:
        """Rename a TV or switch its monitoring on or off (needs the admin scope)."""
        body: dict[str, Any] = {}
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        return _tv(await self._request("PATCH", f"/api/v1/tvs/{tv_id}", body))

    async def me(self) -> Caller:
        raw = await self._request("GET", "/api/v1/auth/me")
        return Caller(kind=raw["kind"], scopes=tuple(raw["scopes"]))

    async def override(
        self,
        tv_id: str,
        *,
        allow: bool,
        minutes: int | None = None,
        until_midnight: bool = False,
    ) -> Override:
        """Allow or block a TV for ``minutes``, or until the household's midnight."""
        body: dict[str, Any] = {"allow": allow, "until_midnight": until_midnight}
        if minutes is not None:
            body["minutes"] = minutes
        return _override(await self._request("POST", f"/api/v1/tvs/{tv_id}/override", body))

    async def clear_override(self, tv_id: str) -> None:
        await self._request("DELETE", f"/api/v1/tvs/{tv_id}/override")

    async def bonus(self, tv_id: str, minutes: int) -> int:
        """Grant extra minutes for today; returns all the bonus minutes granted today."""
        raw = await self._request("POST", f"/api/v1/tvs/{tv_id}/bonus", {"minutes": minutes})
        return int(raw["bonus_minutes"])

    async def pause(self, tv_id: str, minutes: int = 30) -> Override:
        return _override(
            await self._request("POST", f"/api/v1/tvs/{tv_id}/pause", {"minutes": minutes})
        )

    async def activate_profile(
        self,
        policy_id: int,
        *,
        minutes: int | None = None,
        until_midnight: bool = False,
        excluded_tv_ids: list[str] | None = None,
    ) -> ActiveProfile:
        """Put a rule set in force for the household, except for the TVs left out (Pro)."""
        body: dict[str, Any] = {
            "policy_id": policy_id,
            "until_midnight": until_midnight,
            "excluded_tv_ids": excluded_tv_ids or [],
            "source": "automation",
        }
        if minutes is not None:
            body["minutes"] = minutes
        raw = await self._request("POST", "/api/v1/profiles/active", body)
        return ActiveProfile(
            policy_id=raw["policy_id"],
            name=raw["name"],
            until=datetime.fromisoformat(raw["ends_at"]),
            source=raw["source"],
        )

    async def stop_profile(self) -> None:
        await self._request("DELETE", "/api/v1/profiles/active")

    async def events(self) -> AsyncIterator[Event]:
        """Live events: the status of every TV first, then each event as it happens.

        Keep-alive pings are skipped. The iteration ends when the Engine closes the socket and
        raises ``AuthenticationError`` if it did so because of the credentials.
        """
        url = self._base_url.replace("http", "ws", 1) + "/api/v1/events/ws"
        try:
            async with self._http().ws_connect(url, headers=self._headers(), **self._tls) as ws:
                async for message in ws:
                    if message.type is not aiohttp.WSMsgType.TEXT:
                        break
                    raw = message.json()
                    if raw["type"] == "ping":
                        continue
                    yield Event(
                        type=raw["type"],
                        tv_id=raw["tv_id"],
                        at=datetime.fromisoformat(raw["at"]) if raw["at"] else None,
                        payload=raw["payload"],
                    )
                if ws.close_code in (WS_UNAUTHENTICATED, WS_FORBIDDEN):
                    raise AuthenticationError(
                        "the Engine closed the event stream: sign-in required",
                        status=401 if ws.close_code == WS_UNAUTHENTICATED else 403,
                    )
        except aiohttp.ClientConnectorCertificateError as ex:
            raise CertificateError(f"{self._base_url}: {ex}") from ex
        except aiohttp.ClientConnectionError as ex:
            raise TVBalanceConnectionError(f"cannot reach {self._base_url}: {ex}") from ex
