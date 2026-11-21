"""HTTPS on the local network: certificate status, the CA devices must trust, and its rotation."""

from __future__ import annotations

import ipaddress
from dataclasses import asdict

from fastapi import APIRouter, Request, Response

from tvbalance.api.deps import FullAdmin
from tvbalance.api.errors import ApiError, not_found
from tvbalance.api.schemas.errors import AUTH_ERRORS, ErrorResponse
from tvbalance.api.schemas.tls import TlsStatusOut
from tvbalance.app.tls import TlsManager, TlsStatus
from tvbalance.infra import tls

router = APIRouter(prefix="/api/v1/tls", tags=["tls"])

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _manager(request: Request) -> TlsManager:
    manager: TlsManager = request.app.state.tls
    return manager


def _host(name: str) -> str:
    try:
        return f"[{name}]" if ipaddress.ip_address(name).version == 6 else name
    except ValueError:
        return name


def _out(status: TlsStatus) -> TlsStatusOut:
    reachable = [name for name in status.names if name not in LOOPBACK] or status.names
    urls = (
        [f"https://{_host(name)}:{status.https_port}" for name in reachable]
        if status.active
        else []
    )
    return TlsStatusOut(**asdict(status), urls=urls)


@router.get("", response_model=TlsStatusOut, responses=AUTH_ERRORS)
async def tls_status(_: FullAdmin, request: Request) -> TlsStatusOut:
    return _out(_manager(request).status())


@router.get("/ca.crt", responses={404: {"model": ErrorResponse}})
async def ca_certificate(request: Request) -> Response:
    """Public: a certificate is not a secret; Settings shows its fingerprint to compare."""
    cert = _manager(request).ca_certificate()
    if cert is None:
        raise not_found("CA certificate")
    return Response(
        tls.cert_pem(cert),
        media_type="application/x-x509-ca-cert",
        headers={"Content-Disposition": 'attachment; filename="tvbalance-ca.crt"'},
    )


@router.get("/ca.mobileconfig", responses={404: {"model": ErrorResponse}})
async def ca_profile(request: Request) -> Response:
    """Public: an iOS/macOS profile that installs the same CA."""
    cert = _manager(request).ca_certificate()
    if cert is None:
        raise not_found("CA certificate")
    return Response(
        tls.mobileconfig(cert),
        media_type="application/x-apple-aspen-config",
        headers={"Content-Disposition": 'attachment; filename="tvbalance-ca.mobileconfig"'},
    )


@router.post(
    "/rotate",
    response_model=TlsStatusOut,
    responses={**AUTH_ERRORS, 409: {"model": ErrorResponse}},
)
async def rotate(_: FullAdmin, request: Request) -> TlsStatusOut:
    """Create a new CA and certificate. Every device must install the new CA."""
    manager = _manager(request)
    try:
        await manager.rotate()
    except tls.TlsError as ex:
        raise ApiError(409, "tls_not_automatic", str(ex)) from ex
    return _out(manager.status())
