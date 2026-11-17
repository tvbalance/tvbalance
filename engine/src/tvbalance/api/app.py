"""FastAPI application factory. Routes are relative-path friendly (Ingress)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tvbalance import __version__
from tvbalance.api.errors import install_error_handlers
from tvbalance.api.routes import activity, auth, control, policies, settings, system, tvs
from tvbalance.api.routes.system import API_VERSION as API_VERSION
from tvbalance.app.auth import AuthService
from tvbalance.app.events import EventBus
from tvbalance.app.status import SupervisorSettings
from tvbalance.app.supervisor import Supervisor
from tvbalance.config import EngineConfig
from tvbalance.infra.clock import SystemClock
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.services import Clock
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.registry import load_plugins


def create_app(
    plugins: dict[str, AdapterPlugin] | None = None,
    web_dir: Path | None = None,
    include_testing: bool = False,
    config: EngineConfig | None = None,
    clock: Clock | None = None,
    supervisor_settings: SupervisorSettings | None = None,
) -> FastAPI:
    """Build the app.

    Pass `plugins` to inject adapters (tests); the default loads entry points.
    `web_dir` is the built web UI, served at `/` after the API routes.
    Testing-only adapters (the fake TV) are listed only when `include_testing` is set.
    With a `config` the storage is opened at startup (running the migrations) and closed at
    shutdown; it is available as `app.state.storage`, next to the authentication service
    (`app.state.auth`), the clock (`app.state.clock`), the event bus (`app.state.events`) and the
    supervisor that watches every paired TV (`app.state.supervisor`). `clock` and
    `supervisor_settings` let tests control time and pacing. Without a config the API serves
    only its public routes.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if config is None:
            yield
            return
        clock_ = clock or SystemClock()
        storage = await open_storage(config, clock_)
        app.state.clock = clock_
        app.state.storage = storage
        app.state.auth = AuthService(storage.auth, clock_)
        app.state.events = EventBus(storage.events)
        app.state.supervisor = Supervisor(
            storage, registered, app.state.events, clock_, supervisor_settings
        )
        try:
            await app.state.supervisor.start()
            yield
        finally:
            await app.state.supervisor.stop()
            await storage.close()

    registered = load_plugins() if plugins is None else plugins
    app = FastAPI(title="TVBalance Engine", version=__version__, lifespan=lifespan)
    app.state.plugins = registered
    app.state.include_testing = include_testing
    app.state.ingress_trusted = config.ingress_trusted if config else frozenset()
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(tvs.router)
    app.include_router(policies.router)
    app.include_router(control.router)
    app.include_router(activity.router)
    app.include_router(settings.router)

    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app
