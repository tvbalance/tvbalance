"""FastAPI application factory. Routes are relative-path friendly (Ingress)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tvbalance import __version__
from tvbalance.api.errors import install_error_handlers
from tvbalance.api.routes import (
    activity,
    auth,
    control,
    events_ws,
    inventory,
    license,
    pairing,
    policies,
    push,
    settings,
    system,
    tls,
    tvs,
)
from tvbalance.api.routes.system import API_VERSION as API_VERSION
from tvbalance.app.auth import AuthService
from tvbalance.app.events import EventBus
from tvbalance.app.ha_discovery import HomeAssistantDiscovery
from tvbalance.app.licensing import LicenseService
from tvbalance.app.notifications import PushNotifier, load_vapid_keys
from tvbalance.app.pairing import DISCOVERY_TIMEOUT, POLL_INTERVAL, PairingService
from tvbalance.app.status import SupervisorSettings
from tvbalance.app.supervisor import Supervisor
from tvbalance.app.tls import TlsManager
from tvbalance.config import EngineConfig
from tvbalance.infra.clock import SystemClock
from tvbalance.infra.db.repositories import open_storage
from tvbalance.infra.licensing import TRUSTED_PUBLIC_KEYS
from tvbalance.infra.webpush import WebPushSender
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
    discovery_timeout: float = DISCOVERY_TIMEOUT,
    pairing_poll_interval: float = POLL_INTERVAL,
    license_public_keys: Iterable[str] = TRUSTED_PUBLIC_KEYS,
) -> FastAPI:
    """Build the app.

    Pass `plugins` to inject adapters (tests); the default loads entry points.
    `web_dir` is the built web UI, served at `/` after the API routes.
    Testing-only adapters (the fake TV) are listed only when `include_testing` is set.
    With a `config` the storage is opened at startup (running the migrations) and closed at
    shutdown; it is available as `app.state.storage`, next to the authentication service
    (`app.state.auth`), the clock (`app.state.clock`), the event bus (`app.state.events`) and the
    supervisor that watches every paired TV (`app.state.supervisor`), within the limits of the
    license service (`app.state.license`). `clock` and `supervisor_settings` let tests control
    time and pacing; `license_public_keys` are the keys whose licenses count. Without a config
    the API serves only its public routes.
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
        auth_ = app.state.auth = AuthService(storage.auth, clock_)
        app.state.events = EventBus(storage.events)
        license_ = app.state.license = LicenseService(
            storage.secrets,
            app.state.events,
            clock_,
            license_public_keys,
            on_change=lambda: app.state.supervisor.refresh(),
        )
        await license_.load()
        app.state.supervisor = Supervisor(
            storage, registered, app.state.events, clock_, supervisor_settings, license_
        )
        app.state.pairing = PairingService(
            storage,
            registered,
            app.state.supervisor,
            app.state.events,
            clock_,
            include_testing,
            discovery_timeout,
            pairing_poll_interval,
        )
        discovery = None
        if config.supervisor_token:
            discovery = HomeAssistantDiscovery(auth_, storage.secrets, config)
        app.state.ha_discovery = discovery
        tls_manager = app.state.tls = TlsManager(storage.secrets, config, clock_)
        await tls_manager.prepare()
        app.state.vapid_keys = await load_vapid_keys(storage.secrets)
        sender = WebPushSender(app.state.vapid_keys)
        notifier = app.state.push = PushNotifier(storage, app.state.events, sender, clock_)
        try:
            await notifier.start()
            tls_manager.start()
            await app.state.supervisor.start()
            license_.start()
            if discovery:
                discovery.start()
            yield
        finally:
            if discovery:
                await discovery.stop()
            await app.state.pairing.stop()
            await license_.stop()
            await app.state.supervisor.stop()
            await tls_manager.stop()
            await notifier.stop()
            await sender.close()
            await storage.close()

    registered = load_plugins() if plugins is None else plugins
    app = FastAPI(title="TVBalance Engine", version=__version__, lifespan=lifespan)
    app.state.plugins = registered
    app.state.include_testing = include_testing
    app.state.ingress_trusted = config.ingress_trusted if config else frozenset()
    app.state.checkout_url = config.checkout_url if config else ""
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(tvs.router)
    app.include_router(pairing.router)
    app.include_router(push.router)
    app.include_router(tls.router)
    app.include_router(license.router)
    app.include_router(policies.router)
    app.include_router(control.router)
    app.include_router(inventory.router)
    app.include_router(activity.router)
    app.include_router(settings.router)
    app.include_router(events_ws.router)

    if web_dir is not None and web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app
