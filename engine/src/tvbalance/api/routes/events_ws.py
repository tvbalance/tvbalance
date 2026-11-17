"""Live events over a WebSocket: the status of every TV first, then each event as it happens.

Messages are JSON objects ``{"type", "tv_id", "at", "payload"}``. ``type`` is ``status`` for the
snapshot sent on connect (the payload is the TV's status), ``ping`` for the keep-alive, and the
event type (``blocked``, ``time_warning`` ...) otherwise. The socket is closed with code 4401 when
the credential is missing, revoked or expired, and with 4403 when it may not read or the browser's
Origin is not this server.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tvbalance.api.deps import get_auth, get_supervisor, resolve_principal
from tvbalance.api.errors import ApiError
from tvbalance.api.routes.tvs import status_out
from tvbalance.app.auth import Principal
from tvbalance.app.events import BusEvent, EventBus

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

PING_INTERVAL = 30.0
UNAUTHENTICATED = 4401
FORBIDDEN = 4403


async def _principal(ws: WebSocket) -> Principal | None:
    try:
        return await resolve_principal(ws, get_auth(ws), check_csrf=False)
    except ApiError:
        return None


def _same_origin(ws: WebSocket) -> bool:
    """A browser always sends Origin; a page on another site must not ride the cookie."""
    origin = ws.headers.get("origin")
    if origin is None:
        return True  # not a browser
    return urlsplit(origin).netloc == ws.headers.get("host", "")


async def _wait_for_disconnect(ws: WebSocket) -> None:
    with suppress(WebSocketDisconnect, RuntimeError):
        while True:
            await ws.receive_text()


def _message(event: BusEvent) -> dict[str, object]:
    return {
        "type": event.type,
        "tv_id": event.tv_id,
        "at": event.at.isoformat(),
        "payload": event.payload,
    }


@router.websocket("/ws")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    principal = await _principal(ws)
    if principal is None:
        await ws.close(code=UNAUTHENTICATED)
        return
    cookie_auth = principal.kind in ("admin", "pin")
    if "read" not in principal.scopes or (cookie_auth and not _same_origin(ws)):
        await ws.close(code=FORBIDDEN)
        return

    supervisor = get_supervisor(ws)
    bus: EventBus = ws.app.state.events
    async with bus.subscribe() as queue:
        for status in supervisor.statuses():
            shown = status_out(status)
            assert shown is not None
            await ws.send_json(
                {
                    "type": "status",
                    "tv_id": status.tv_id,
                    "at": status.updated_at.isoformat() if status.updated_at else None,
                    "payload": shown.model_dump(mode="json"),
                }
            )
        gone = asyncio.create_task(_wait_for_disconnect(ws))
        try:
            while not gone.done():
                incoming = asyncio.create_task(queue.get())
                await asyncio.wait(
                    {incoming, gone}, timeout=PING_INTERVAL, return_when=asyncio.FIRST_COMPLETED
                )
                if gone.done():
                    incoming.cancel()
                    break
                if await _principal(ws) is None:  # signed out, revoked or expired meanwhile
                    incoming.cancel()
                    await ws.close(code=UNAUTHENTICATED)
                    break
                if incoming.done():
                    await ws.send_json(_message(incoming.result()))
                else:
                    incoming.cancel()
                    await ws.send_json({"type": "ping", "tv_id": None, "at": None, "payload": {}})
        except (WebSocketDisconnect, RuntimeError):
            pass  # the client went away while we were sending
        finally:
            gone.cancel()
            with suppress(asyncio.CancelledError):
                await gone
