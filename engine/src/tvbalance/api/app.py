"""FastAPI application factory. Routes are relative-path friendly (Ingress)."""

from __future__ import annotations

from fastapi import FastAPI

from tvbalance import __version__
from tvbalance.api.schemas import AdapterOut, HealthResponse, InfoResponse
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.registry import load_plugins

API_VERSION = "1"


def create_app(plugins: dict[str, AdapterPlugin] | None = None) -> FastAPI:
    """Build the app. Pass `plugins` to inject adapters (tests); default loads entry points."""
    app = FastAPI(title="TVBalance Engine", version=__version__)
    registered = load_plugins() if plugins is None else plugins

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/api/v1/info", response_model=InfoResponse, tags=["system"])
    async def info() -> InfoResponse:
        return InfoResponse(
            version=__version__,
            api_version=API_VERSION,
            adapters=[
                AdapterOut(
                    id=p.info.id,
                    brand=p.info.brand,
                    display_name=p.info.display_name,
                    maturity=p.info.maturity,
                    capabilities=sorted(p.info.capabilities),
                )
                for p in sorted(registered.values(), key=lambda p: p.info.id)
            ],
        )

    return app
