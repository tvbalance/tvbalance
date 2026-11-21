"""Web Push: which devices get notified, and the key their browsers subscribe with."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, Response

from tvbalance.api.deps import FullAdmin, get_storage
from tvbalance.api.errors import not_found
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.api.schemas.push import (
    PushEvent,
    PushKeyOut,
    PushSubscriptionCreate,
    PushSubscriptionOut,
    PushSubscriptionUpdate,
    PushTestOut,
)
from tvbalance.app.notifications import PushNotifier
from tvbalance.infra.webpush import VapidKeys
from tvbalance.ports.storage import PushSubscriptionRecord, Storage

router = APIRouter(prefix="/api/v1/push", tags=["push"])

StorageDep = Annotated[Storage, Depends(get_storage)]
USER_AGENT_LIMIT = 200


def _out(record: PushSubscriptionRecord, current: bool = False) -> PushSubscriptionOut:
    return PushSubscriptionOut(
        id=record.id,
        events=cast(list[PushEvent], sorted(record.events)),
        language=record.language,
        user_agent=record.user_agent,
        created_at=record.created_at,
        last_sent_at=record.last_sent_at,
        current=current,
    )


@router.get("/key", response_model=PushKeyOut, responses=AUTH_ERRORS)
async def push_key(_: FullAdmin, request: Request) -> PushKeyOut:
    keys: VapidKeys = request.app.state.vapid_keys
    return PushKeyOut(public_key=keys.public_key)


@router.get("/subscriptions", response_model=list[PushSubscriptionOut], responses=AUTH_ERRORS)
async def list_subscriptions(
    _: FullAdmin,
    storage: StorageDep,
    endpoint: Annotated[str | None, Query(description="Marks this browser's own entry.")] = None,
) -> list[PushSubscriptionOut]:
    return [_out(r, current=r.endpoint == endpoint) for r in await storage.push.list()]


@router.post(
    "/subscriptions",
    response_model=PushSubscriptionOut,
    responses={**AUTH_ERRORS, 201: {"model": PushSubscriptionOut}},
)
async def subscribe(
    body: PushSubscriptionCreate,
    _: FullAdmin,
    storage: StorageDep,
    request: Request,
    response: Response,
) -> PushSubscriptionOut:
    """Register this browser, or refresh it when the endpoint is already known."""
    record, created = await storage.push.upsert(
        body.endpoint,
        body.keys.p256dh,
        body.keys.auth,
        frozenset(body.events),
        body.language,
        body.app_url,
        request.headers.get("user-agent", "")[:USER_AGENT_LIMIT],
    )
    response.status_code = 201 if created else 200
    return _out(record, current=True)


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=PushSubscriptionOut,
    responses=NOT_FOUND_ERRORS,
)
async def change_events(
    subscription_id: str, body: PushSubscriptionUpdate, _: FullAdmin, storage: StorageDep
) -> PushSubscriptionOut:
    if not await storage.push.update_events(subscription_id, frozenset(body.events)):
        raise not_found("subscription")
    record = await storage.push.get(subscription_id)
    if record is None:
        raise not_found("subscription")
    return _out(record)


@router.delete("/subscriptions/{subscription_id}", status_code=204, responses=NOT_FOUND_ERRORS)
async def unsubscribe(subscription_id: str, _: FullAdmin, storage: StorageDep) -> Response:
    if not await storage.push.delete(subscription_id):
        raise not_found("subscription")
    return Response(status_code=204)


@router.post(
    "/subscriptions/{subscription_id}/test",
    response_model=PushTestOut,
    responses=NOT_FOUND_ERRORS,
)
async def send_test(
    subscription_id: str, _: FullAdmin, storage: StorageDep, request: Request
) -> PushTestOut:
    record = await storage.push.get(subscription_id)
    if record is None:
        raise not_found("subscription")
    notifier: PushNotifier = request.app.state.push
    result = await notifier.send_test(record)
    return PushTestOut(result=result.value)
