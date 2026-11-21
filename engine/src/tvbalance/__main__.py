"""Entry point: `python -m tvbalance` or the `tvbalance` script."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
from collections.abc import Iterator

import uvicorn
from fastapi import FastAPI

from tvbalance.api.app import create_app
from tvbalance.app.tls import TlsManager
from tvbalance.config import ConfigError, EngineConfig

log = logging.getLogger(__name__)


class _SecondaryServer(uvicorn.Server):
    """A listener that leaves signal handling to the main one."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


async def _serve_https(server: uvicorn.Server) -> None:
    try:
        await server.serve()
    except (OSError, SystemExit) as ex:
        log.error("HTTPS is not available: %s", ex or "the port could not be opened")


async def serve(
    config: EngineConfig,
    app: FastAPI | None = None,
    stop: asyncio.Event | None = None,
) -> None:
    """Serve HTTP and, when a certificate is ready, HTTPS on a second port.

    `stop` lets a caller end both listeners without a signal (tests).
    """
    app = app or create_app(web_dir=config.web_dir, config=config)
    http = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port, log_level="info"))
    http_task = asyncio.create_task(http.serve(), name="http")
    while not http.started and not http_task.done():  # noqa: ASYNC110 - no startup event in uvicorn
        await asyncio.sleep(0.05)

    https: _SecondaryServer | None = None
    https_task: asyncio.Task[None] | None = None
    manager: TlsManager | None = getattr(app.state, "tls", None)
    if http.started and manager is not None and manager.active:
        https = _SecondaryServer(
            uvicorn.Config(
                app,
                host=config.host,
                port=config.https_port,
                ssl_certfile=manager.certfile,
                ssl_keyfile=manager.keyfile,
                lifespan="off",
                log_level="info",
            )
        )
        manager.on_renew(lambda: _reload(https, manager))
        https_task = asyncio.create_task(_serve_https(https), name="https")

    watcher = asyncio.create_task(_stop_on(stop, http, https)) if stop else None
    try:
        await http_task
    finally:
        if watcher:
            watcher.cancel()
        if https is not None and https_task is not None:
            https.should_exit = True
            await https_task


async def _stop_on(stop: asyncio.Event, http: uvicorn.Server, https: uvicorn.Server | None) -> None:
    await stop.wait()
    http.should_exit = True
    if https is not None:
        https.should_exit = True


def _reload(server: uvicorn.Server, manager: TlsManager) -> None:
    """Let new connections use the renewed certificate; open ones keep the old one."""
    context = server.config.ssl
    if context is None or manager.certfile is None:
        return
    context.load_cert_chain(manager.certfile, manager.keyfile)
    log.info("HTTPS now serves the renewed certificate")


def main() -> None:
    try:
        config = EngineConfig.from_env(os.environ)
    except ConfigError as ex:
        sys.exit(f"tvbalance: {ex}")
    asyncio.run(serve(config))


if __name__ == "__main__":
    main()
