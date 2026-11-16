"""Liveness, version and the adapters this engine can drive."""

from __future__ import annotations

from fastapi import APIRouter, Request

from tvbalance import __version__
from tvbalance.api.deps import CanRead
from tvbalance.api.schemas.errors import ErrorResponse
from tvbalance.api.schemas.system import AdapterOut, HealthResponse, InfoResponse

API_VERSION = "1"

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Public: the Add-on watchdog and load balancers poll it."""
    return HealthResponse(status="ok")


@router.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    """Public: enough for a client to check it talks to a compatible engine."""
    return InfoResponse(version=__version__, api_version=API_VERSION)


@router.get(
    "/adapters",
    response_model=list[AdapterOut],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def adapters(request: Request, _: CanRead) -> list[AdapterOut]:
    include_testing: bool = request.app.state.include_testing
    return [
        AdapterOut(
            id=p.info.id,
            brand=p.info.brand,
            display_name=p.info.display_name,
            maturity=p.info.maturity,
            capabilities=sorted(p.info.capabilities),
        )
        for p in sorted(request.app.state.plugins.values(), key=lambda p: p.info.id)
        if include_testing or not p.info.testing_only
    ]
