"""The Pro license: read the plan, paste a key, remove it."""

from __future__ import annotations

from fastapi import APIRouter, Request

from tvbalance.api.deps import CanRead, FullAdmin
from tvbalance.api.errors import ApiError
from tvbalance.api.schemas.errors import AUTH_ERRORS, ErrorResponse
from tvbalance.api.schemas.license import LicenseKeyIn, LicenseOut
from tvbalance.app.licensing import LicenseService
from tvbalance.infra.licensing import LicenseError

router = APIRouter(prefix="/api/v1/license", tags=["license"])


def _service(request: Request) -> LicenseService:
    service: LicenseService | None = getattr(request.app.state, "license", None)
    if service is None:
        raise ApiError(503, "unavailable", "the engine is not ready")
    return service


def _out(request: Request) -> LicenseOut:
    info = _service(request).info()
    return LicenseOut(
        status=info.status,
        tier=info.tier,
        licensee=info.licensee,
        expires_at=info.expires_at,
        max_tvs=info.max_tvs,
        checkout_url=request.app.state.checkout_url,
    )


@router.get("", response_model=LicenseOut, responses=AUTH_ERRORS)
async def read_license(_: CanRead, request: Request) -> LicenseOut:
    return _out(request)


@router.put("", response_model=LicenseOut, responses={**AUTH_ERRORS, 422: {"model": ErrorResponse}})
async def activate_license(body: LicenseKeyIn, _: FullAdmin, request: Request) -> LicenseOut:
    try:
        await _service(request).activate(body.key)
    except LicenseError as ex:
        raise ApiError(422, "invalid_license", str(ex)) from ex
    return _out(request)


@router.delete("", response_model=LicenseOut, responses=AUTH_ERRORS)
async def remove_license(_: FullAdmin, request: Request) -> LicenseOut:
    await _service(request).remove()
    return _out(request)
