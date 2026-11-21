"""The apps, inputs and channels of a connected TV, for the rule editor's pickers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from tvbalance.api.deps import CanRead, get_storage, get_supervisor
from tvbalance.api.errors import ApiError, not_found
from tvbalance.api.routes.tvs import existing_tv
from tvbalance.api.schemas.errors import NOT_FOUND_ERRORS, Responses
from tvbalance.api.schemas.inventory import AppOut, ChannelOut, InputOut, InventoryOut
from tvbalance.app.icons import IconUnavailable, fetch_icon
from tvbalance.app.status import Inventory
from tvbalance.app.supervisor import Supervisor
from tvbalance.ports.storage import Storage
from tvbalance.sdk.errors import TVError

router = APIRouter(prefix="/api/v1/tvs/{tv_id}", tags=["inventory"])

StorageDep = Annotated[Storage, Depends(get_storage)]
SupervisorDep = Annotated[Supervisor, Depends(get_supervisor)]

INVENTORY_ERRORS: Responses = {**NOT_FOUND_ERRORS, 409: NOT_FOUND_ERRORS[404]}


def tv_offline() -> ApiError:
    return ApiError(409, "tv_offline", "The TV is not connected right now")


async def listed_inventory(tv_id: str, storage: Storage, supervisor: Supervisor) -> Inventory:
    await existing_tv(storage, tv_id)
    try:
        listed = await supervisor.inventory(tv_id)
    except TVError as ex:
        raise tv_offline() from ex
    if listed is None:
        raise tv_offline()
    return listed


@router.get("/inventory", response_model=InventoryOut, responses=INVENTORY_ERRORS)
async def inventory(
    tv_id: str, _: CanRead, storage: StorageDep, supervisor: SupervisorDep
) -> InventoryOut:
    """Cached for a few minutes. ``409 tv_offline`` while the TV is disabled or unreachable."""
    listed = await listed_inventory(tv_id, storage, supervisor)
    return InventoryOut(
        apps=[
            AppOut(id=a.app_id, name=a.name, has_icon=a.icon_url is not None) for a in listed.apps
        ],
        inputs=[InputOut(id=i.input_id, label=i.label) for i in listed.inputs],
        channels=[
            ChannelOut(id=c.channel_id, name=c.name, number=c.number) for c in listed.channels
        ],
    )


@router.get(
    "/apps/{app_id}/icon",
    response_class=Response,
    responses={**INVENTORY_ERRORS, 502: NOT_FOUND_ERRORS[404], 200: {"content": {"image/*": {}}}},
)
async def app_icon(
    tv_id: str, app_id: str, _: CanRead, storage: StorageDep, supervisor: SupervisorDep
) -> Response:
    """The app's icon, fetched from the TV: the browser cannot reach the TV's own address."""
    record = await existing_tv(storage, tv_id)
    listed = await listed_inventory(tv_id, storage, supervisor)
    icon_url = next((a.icon_url for a in listed.apps if a.app_id == app_id), None)
    if icon_url is None:
        raise not_found("icon")
    try:
        body, media_type = await fetch_icon(icon_url, record.host)
    except IconUnavailable as ex:
        raise ApiError(502, "icon_unavailable", str(ex)) from ex
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",  # an SVG must not run scripts
        },
    )
