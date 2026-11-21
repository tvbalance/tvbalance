"""Finding TVs on the network and pairing them. Admin only: a PIN session never adds TVs."""

from __future__ import annotations

from fastapi import APIRouter

from tvbalance.api.deps import CanAdmin, PairingDep
from tvbalance.api.schemas.errors import AUTH_ERRORS
from tvbalance.api.schemas.pairing import FoundTvOut

router = APIRouter(prefix="/api/v1", tags=["pairing"])


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
