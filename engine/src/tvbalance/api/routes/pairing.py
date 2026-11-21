"""Finding TVs on the network and pairing them. Admin only: a PIN session never adds TVs."""

from __future__ import annotations

from fastapi import APIRouter, Response

from tvbalance.api.deps import CanAdmin, PairingDep
from tvbalance.api.errors import ApiError
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.api.schemas.pairing import FoundTvOut, PairingOut, PairingStart
from tvbalance.app.pairing import AdapterMismatch, AlreadyAdded, PairingError, PairingSession

router = APIRouter(prefix="/api/v1", tags=["pairing"])

_STATUS: dict[type[PairingError], int] = {AlreadyAdded: 409, AdapterMismatch: 409}


def _api_error(error: PairingError) -> ApiError:
    return ApiError(_STATUS.get(type(error), 404), error.code, str(error))


def _out(session: PairingSession) -> PairingOut:
    return PairingOut(
        id=session.id,
        state=session.state.value,
        adapter_id=session.adapter_id,
        host=session.host,
        tv_id=session.tv_id,
        expires_at=session.expires_at,
    )


@router.get("/discovery", response_model=list[FoundTvOut], responses=AUTH_ERRORS)
async def discovery(_: CanAdmin, pairing: PairingDep) -> list[FoundTvOut]:
    """Search the network with every installed adapter; takes a few seconds."""
    return [
        FoundTvOut(
            adapter_id=f.adapter_id,
            adapter_name=f.adapter_name,
            host=f.host,
            name=f.name,
            model=f.model,
            already_added=f.already_added,
        )
        for f in await pairing.discover()
    ]


@router.post("/pairings", status_code=201, response_model=PairingOut, responses=NOT_FOUND_ERRORS)
async def start_pairing(body: PairingStart, _: CanAdmin, pairing: PairingDep) -> PairingOut:
    """Start pairing a TV: it asks its owner to accept, and the TV is stored once they do.

    With ``tv_id`` a stored TV is paired again (its key was lost); its key is replaced.
    """
    try:
        return _out(await pairing.start(body.adapter_id, body.host, body.name, body.tv_id))
    except PairingError as error:
        raise _api_error(error) from error


@router.get("/pairings/{pairing_id}", response_model=PairingOut, responses=NOT_FOUND_ERRORS)
async def get_pairing(pairing_id: str, _: CanAdmin, pairing: PairingDep) -> PairingOut:
    try:
        return _out(pairing.get(pairing_id))
    except PairingError as error:
        raise _api_error(error) from error


@router.delete("/pairings/{pairing_id}", status_code=204, responses=NOT_FOUND_ERRORS)
async def cancel_pairing(pairing_id: str, _: CanAdmin, pairing: PairingDep) -> Response:
    """Abandon a pairing (the person left the wizard). A TV already stored stays."""
    try:
        await pairing.cancel(pairing_id)
    except PairingError as error:
        raise _api_error(error) from error
    return Response(status_code=204)
