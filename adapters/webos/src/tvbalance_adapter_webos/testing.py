"""An in-process SSAP websocket server that behaves like a webOS TV (tests, contract suite)."""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from aiohttp import WSMsgType, web

from tvbalance.domain.models import Power
from tvbalance.sdk.types import AdapterConfig
from tvbalance_adapter_webos import _client

LIVETV = "com.webos.app.livetv"
_counter = itertools.count(1)

POWER_STATES = {
    Power.ON: "Active",
    Power.STANDBY: "Active Standby",
    Power.OFF: "Power Off",
}

CHANNELS = [
    {"channelId": "ch-one", "channelNumber": "1", "channelName": "One HD"},
    {"channelId": "ch-news", "channelNumber": "7", "channelName": "News 24"},
]
INPUTS = [
    {"id": "HDMI_1", "label": "HDMI 1", "appId": "com.webos.app.hdmi1"},
    {"id": "HDMI_2", "label": "HDMI 2", "appId": "com.webos.app.hdmi2"},
]
APPS = [
    {"id": "video", "title": "Video Streaming", "icon": "https://tv.invalid:3001/icons/v.png"},
    {"id": "kids", "title": "Kids Corner", "icon": ""},
]

_ACTION_URIS = {
    "system.notifications/createToast",
    "com.webos.applicationManager/launch",
    "tv/switchInput",
    "tv/openChannel",
    "system/turnOff",
}
_POWER_URI = "com.webos.service.tvpower/power/getPowerState"
_APP_URI = "com.webos.applicationManager/getForegroundAppInfo"


@dataclass
class _Subscription:
    ws: web.WebSocketResponse
    msg_id: Any
    uri: str


@dataclass
class SimulatedWebOsTV:
    """State, knobs and a command log. ``start()`` serves it on a free loopback port."""

    host: str = field(default_factory=lambda: f"sim-{next(_counter)}.invalid")
    client_key: str = "sim-client-key"
    power_state: str = "Active"
    app_id: str = LIVETV
    channel: dict[str, str] = field(default_factory=lambda: dict(CHANNELS[1]))
    program_name: str | None = "Evening News"
    junk_rows: bool = False  # non-dict rows in plain (non-subscription) list responses
    mute: bool = False  # keep the socket open but never answer a request
    pairing_prompt: str = "accept"  # "accept" | "reject" | "hold" (wait for answer_prompt)
    commands: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    registered_keys: list[str | None] = field(default_factory=list)
    port: int = 0

    _runner: web.AppRunner | None = field(default=None, repr=False)
    _sockets: set[web.WebSocketResponse] = field(default_factory=set, repr=False)
    _subs: list[_Subscription] = field(default_factory=list, repr=False)
    _answer: asyncio.Future[bool] | None = field(default=None, repr=False)

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._main)
        app.router.add_get("/input", self._input)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        _client.SIMULATED_PORTS[self.host] = self.port

    async def stop(self) -> None:
        _client.SIMULATED_PORTS.pop(self.host, None)
        await self.drop()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def drop(self) -> None:
        """Abruptly close every open socket."""
        for ws in list(self._sockets):
            await ws.close()
        self._sockets.clear()
        self._subs.clear()

    def answer_prompt(self, accept: bool) -> None:
        """Resolve a pairing prompt held with ``pairing_prompt = "hold"``."""
        if self._answer is not None and not self._answer.done():
            self._answer.set_result(accept)

    async def set_power(self, power: Power) -> None:
        self.power_state = POWER_STATES[power]
        await self._push(_POWER_URI)

    async def set_app(self, app_id: str) -> None:
        self.app_id = app_id
        await self._push(_APP_URI)

    # -- protocol ---------------------------------------------------------------------------

    def _payload(self, uri: str, payload: dict[str, Any], *, subscribing: bool) -> dict[str, Any]:
        ok: dict[str, Any] = {"returnValue": True}
        if subscribing:
            ok["subscribed"] = True
        junk: list[Any] = ["BOGUS"] if self.junk_rows and not subscribing else []
        if uri in _ACTION_URIS:
            self.commands.append((uri, payload))
            return ok
        match uri:
            case "com.webos.service.tvpower/power/getPowerState":
                return {**ok, "state": self.power_state}
            case "com.webos.applicationManager/getForegroundAppInfo":
                return {**ok, "appId": self.app_id}
            case "com.webos.applicationManager/listLaunchPoints":
                return {**ok, "launchPoints": [*APPS, *junk]}
            case "tv/getExternalInputList":
                return {**ok, "devices": [*INPUTS, *junk]}
            case "tv/getChannelList":
                if subscribing:  # unsubscribable: keeps the library from its 2 s livetv delay
                    return {}
                return {**ok, "channelList": [*CHANNELS, *junk]}
            case "tv/getCurrentChannel":
                return {**ok, **self.channel}
            case "tv/getChannelCurrentProgramInfo":
                if self.program_name is None:
                    return {"returnValue": False, "errorText": "no program"}
                return {**ok, "programName": self.program_name}
            case "com.webos.service.networkinput/getPointerInputSocket":
                return {**ok, "socketPath": f"ws://127.0.0.1:{self.port}/input"}
            case "audio/getStatus" | "audio/getVolume":
                return {**ok, "volume": 10, "volumeStatus": {"volume": 10, "muteStatus": False}}
            case "com.webos.service.apiadapter/audio/getSoundOutput":
                return {**ok, "soundOutput": "tv_speaker"}
            case "com.webos.media/getForegroundAppInfo":
                return {**ok, "foregroundAppInfo": []}
            case "system/getSystemInfo":
                return {**ok, "modelName": "SIM-TV"}
            case "com.webos.service.update/getCurrentSWInformation":
                return {**ok, "product_name": "webOS", "major_ver": "4"}
        return {}

    async def _respond(self, ws: web.WebSocketResponse, msg: dict[str, Any]) -> None:
        uri = str(msg.get("uri", "")).removeprefix("ssap://")
        subscribing = msg.get("type") == "subscribe"
        payload = self._payload(uri, msg.get("payload") or {}, subscribing=subscribing)
        if not payload:
            error = "404 no such service or method"
            await ws.send_json({"type": "error", "id": msg["id"], "error": error, "payload": {}})
            return
        if subscribing:
            self._subs.append(_Subscription(ws, msg["id"], uri))
        await ws.send_json({"type": "response", "id": msg["id"], "payload": payload})

    async def _push(self, uri: str) -> None:
        for sub in [s for s in self._subs if s.uri == uri]:
            payload = self._payload(uri, {}, subscribing=True)
            await sub.ws.send_json({"type": "response", "id": sub.msg_id, "payload": payload})

    async def _register(self, ws: web.WebSocketResponse, msg: dict[str, Any]) -> bool:
        key = (msg.get("payload") or {}).get("client-key")
        self.registered_keys.append(key)
        if key == self.client_key:
            await ws.send_json({"type": "registered", "id": msg["id"], "payload": {}})
            return True
        prompt = {"pairingType": "PROMPT", "returnValue": True}
        await ws.send_json({"type": "response", "id": msg["id"], "payload": prompt})
        if self.pairing_prompt == "hold":
            self._answer = asyncio.get_running_loop().create_future()
            accepted = await self._answer
        else:
            accepted = self.pairing_prompt == "accept"
        if not accepted:
            await ws.send_json({"type": "error", "id": msg["id"], "error": "403 User denied"})
            return False
        granted = {"client-key": self.client_key}
        await ws.send_json({"type": "registered", "id": msg["id"], "payload": granted})
        return True

    async def _main(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._sockets.add(ws)
        async for raw in ws:
            if raw.type is not WSMsgType.TEXT:
                break
            msg = raw.json()
            if msg["type"] == "hello":
                hello = {"type": "hello", "id": "hello", "payload": {"protocolVersion": 1}}
                await ws.send_json(hello)
            elif msg["type"] == "register":
                if not await self._register(ws, msg):
                    break
            elif self.mute:
                continue
            else:
                await self._respond(ws, msg)
        self._sockets.discard(ws)
        return ws

    async def _input(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._sockets.add(ws)
        async for raw in ws:
            if raw.type is not WSMsgType.TEXT:
                break
            fields = dict(line.split(":", 1) for line in raw.data.splitlines() if ":" in line)
            if fields.get("type") == "button":
                self.buttons.append(fields["name"])
        self._sockets.discard(ws)
        return ws


@dataclass
class _Harness:
    tv: SimulatedWebOsTV
    config: AdapterConfig

    async def set_power(self, power: Power) -> None:
        await self.tv.set_power(power)

    async def drop_connection(self) -> None:
        await self.tv.drop()


@asynccontextmanager
async def harness() -> AsyncIterator[_Harness]:
    """Contract-suite entry point: a paired, running simulator."""
    tv = SimulatedWebOsTV()
    await tv.start()
    try:
        yield _Harness(tv, AdapterConfig(host=tv.host, credentials={"client_key": tv.client_key}))
    finally:
        await tv.stop()
