"""The LG webOS adapter. Timeouts are applied by TVSession, never here."""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import aiohttp
from aiowebostv import WebOsClient, WebOsTvPairError, WebOsTvServiceNotFoundError
from aiowebostv.exceptions import WebOsTvError

from tvbalance.domain.models import (
    Action,
    GoHome,
    LaunchApp,
    Observation,
    Power,
    PowerOff,
    SetChannel,
    SetInput,
    ShowMessage,
)
from tvbalance.ports.tv import PairingFlow
from tvbalance.sdk.errors import TVError, TVPairingError, UnsupportedCapabilityError
from tvbalance.sdk.messages import default_text
from tvbalance.sdk.types import AdapterConfig, AppInfo, Capability, ChannelInfo, InputInfo
from tvbalance_adapter_webos import mapping
from tvbalance_adapter_webos._client import RedirectingSession, make_client
from tvbalance_adapter_webos.info import INFO
from tvbalance_adapter_webos.pairing import WebOsPairing

_PROGRAM_URI = "tv/getChannelCurrentProgramInfo"

_REQUIRED: dict[type[Action], Capability] = {
    ShowMessage: Capability.ON_SCREEN_MESSAGE,
    GoHome: Capability.GO_HOME,
    LaunchApp: Capability.LAUNCH_APP,
    SetInput: Capability.SET_INPUT,
    SetChannel: Capability.SET_CHANNEL,
    PowerOff: Capability.POWER_OFF,
}

_LIBRARY_ERRORS = (WebOsTvError, OSError, aiohttp.ClientError, TimeoutError)


class WebOsAdapter:
    def __init__(self, config: AdapterConfig) -> None:
        self._host = config.host
        self._key = config.credentials.get("client_key")
        self._client: WebOsClient | None = None
        self._session: RedirectingSession | None = None
        self._listeners: list[Callable[[], None]] = []

    # -- lifecycle --------------------------------------------------------------------------

    async def connect(self) -> None:
        if self._client is not None:
            return
        if not self._key:
            # Connecting without a key would pop a pairing prompt on the TV unannounced.
            raise TVPairingError("no client key: pairing is required")
        client, session = make_client(self._host, self._key)
        await client.register_state_update_callback(self._state_changed)
        try:
            await client.connect()
        except WebOsTvPairError as ex:
            await self._discard(client, session)
            raise TVPairingError(f"the TV refused the stored key: {ex}") from ex
        except _LIBRARY_ERRORS as ex:
            await self._discard(client, session)
            raise TVError(f"cannot connect to {self._host}: {ex!r}") from ex
        self._client, self._session = client, session

    async def close(self) -> None:
        client, session = self._client, self._session
        self._client = self._session = None
        if client is not None:
            await self._discard(client, session)

    @staticmethod
    async def _discard(client: WebOsClient, session: RedirectingSession | None) -> None:
        with contextlib.suppress(*_LIBRARY_ERRORS):
            await client.disconnect()
        if session is not None:
            await session.close()

    def _connected(self) -> WebOsClient:
        if self._client is None:
            raise TVError("not connected")
        return self._client

    # -- push -------------------------------------------------------------------------------

    def on_change(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def unsubscribe() -> None:
            with contextlib.suppress(ValueError):
                self._listeners.remove(callback)

        return unsubscribe

    async def _state_changed(self, _state: object) -> None:
        for listener in list(self._listeners):
            listener()

    # -- observation ------------------------------------------------------------------------

    async def _call[T](self, request: Awaitable[T]) -> T:
        try:
            return await request
        except _LIBRARY_ERRORS as ex:
            raise TVError(f"{self._host}: {ex!r}") from ex

    async def observe(self) -> Observation:
        client = self._connected()
        # Always ask the TV: reading only the cache would report a dead peer as still online.
        state: str | None
        try:
            state = (await self._call(client.get_power_state())).get("state")
        except TVError as ex:
            if not isinstance(ex.__cause__, WebOsTvServiceNotFoundError):
                raise
            state = client.tv_state.power_state.get("state")  # very old firmware
        power = mapping.power_from_state(state)
        now = datetime.now(UTC)
        if power is not Power.ON:
            return Observation(observed_at=now, power=power)

        app, input_id, livetv = mapping.split_foreground(
            client.tv_state.current_app_id, client.tv_state.inputs.values()
        )
        channel_id = program = None
        if livetv:
            channel_id, program = await self._current_channel(client)
        return Observation(now, power, app, input_id, channel_id, program)

    async def _current_channel(self, client: WebOsClient) -> tuple[str | None, str | None]:
        try:
            channel = await self._call(client.get_current_channel())
        except TVError:
            return None, None
        channel_id = channel.get("channelId")
        if not channel_id:
            return None, None
        program: str | None = None
        # Program info works only while live TV is in front and is missing on older webOS.
        with contextlib.suppress(TVError):
            info = await self._call(client.request(_PROGRAM_URI, {"channelId": channel_id}))
            program = info.get("programName") or None
        return str(channel_id), program

    # -- inventory --------------------------------------------------------------------------

    async def list_apps(self) -> list[AppInfo]:
        return mapping.app_infos(await self._call(self._connected().get_apps()))

    async def list_inputs(self) -> list[InputInfo]:
        return mapping.input_infos(await self._call(self._connected().get_inputs()))

    async def list_channels(self) -> list[ChannelInfo]:
        return mapping.channel_infos(await self._call(self._connected().get_channels()))

    # -- actions ----------------------------------------------------------------------------

    async def execute(self, action: Action) -> None:
        needed = _REQUIRED[type(action)]
        if needed not in INFO.capabilities:
            raise UnsupportedCapabilityError(f"webos does not declare {needed}")
        client = self._connected()
        send: Awaitable[Any]
        match action:
            case ShowMessage():
                send = client.send_message(default_text(action))
            case GoHome():
                send = client.button("HOME")
            case LaunchApp(app_id):
                send = client.launch_app(app_id)
            case SetInput(input_id):
                send = client.set_input(input_id)
            case SetChannel(channel_id):
                send = client.set_channel(channel_id)  # the id, not the channel object
            case PowerOff():
                send = client.power_off()
        await self._call(send)

    def pairing(self) -> PairingFlow:
        return WebOsPairing(self._host)
