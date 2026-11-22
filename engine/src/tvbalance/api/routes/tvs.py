"""The paired TVs and their live status. Adding a TV (pairing) belongs to the setup flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from tvbalance.api.deps import CanAdmin, CanRead, get_storage, get_supervisor
from tvbalance.api.errors import not_found
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.api.schemas.tvs import DecisionOut, TvOut, TvStatusOut, TvUpdate
from tvbalance.app.status import TvStatus
from tvbalance.app.supervisor import Supervisor
from tvbalance.domain.models import Allow, Block, Decision, Warn
from tvbalance.ports.storage import Storage, TvRecord

router = APIRouter(prefix="/api/v1/tvs", tags=["tvs"])

StorageDep = Annotated[Storage, Depends(get_storage)]
SupervisorDep = Annotated[Supervisor, Depends(get_supervisor)]


def _decision_out(decision: Decision) -> DecisionOut:
    match decision:
        case Allow():
            return DecisionOut(kind="allow")
        case Warn(minutes_left, limit):
            return DecisionOut(kind="warn", minutes_left=minutes_left, limit=limit.value)
        case Block(reason):
            return DecisionOut(kind="block", reason=reason.value)


def status_out(status: TvStatus | None) -> TvStatusOut | None:
    if status is None:
        return None
    seen = status.observation
    return TvStatusOut(
        connected=status.connected,
        pairing_required=status.pairing_required,
        power=seen.power if seen else None,
        foreground_app=seen.foreground_app if seen else None,
        input_id=seen.input_id if seen else None,
        channel_id=seen.channel_id if seen else None,
        program_title=seen.program_title if seen else None,
        decision=_decision_out(status.decision) if status.decision else None,
        watched_seconds=status.watched_seconds,
        remaining_seconds=status.remaining_seconds,
        updated_at=status.updated_at,
    )


def tv_out(record: TvRecord, status: TvStatus | None, plan_limited: bool) -> TvOut:
    return TvOut(
        id=record.id,
        adapter_id=record.adapter_id,
        name=record.name,
        host=record.host,
        policy_id=record.policy_id,
        enabled=record.enabled,
        needs_pairing=record.needs_pairing,
        plan_limited=plan_limited,
        created_at=record.created_at,
        status=status_out(status),
    )


async def existing_tv(storage: Storage, tv_id: str) -> TvRecord:
    record = await storage.tvs.get(tv_id)
    if record is None:
        raise not_found("TV")
    return record


@router.get("", response_model=list[TvOut], responses=AUTH_ERRORS)
async def list_tvs(_: CanRead, storage: StorageDep, supervisor: SupervisorDep) -> list[TvOut]:
    return [
        tv_out(r, supervisor.status(r.id), supervisor.plan_limited(r.id))
        for r in await storage.tvs.list()
    ]


@router.get("/{tv_id}", response_model=TvOut, responses=NOT_FOUND_ERRORS)
async def get_tv(tv_id: str, _: CanRead, storage: StorageDep, supervisor: SupervisorDep) -> TvOut:
    return tv_out(
        await existing_tv(storage, tv_id), supervisor.status(tv_id), supervisor.plan_limited(tv_id)
    )


@router.patch("/{tv_id}", response_model=TvOut, responses=NOT_FOUND_ERRORS)
async def update_tv(
    tv_id: str, body: TvUpdate, _: CanAdmin, storage: StorageDep, supervisor: SupervisorDep
) -> TvOut:
    await existing_tv(storage, tv_id)
    changes = body.model_fields_set
    if body.policy_id is not None and await storage.policies.get(body.policy_id) is None:
        raise not_found("policy")
    if "policy_id" in changes:
        await storage.tvs.assign_policy(tv_id, body.policy_id)
    if body.enabled is not None:
        await storage.tvs.set_enabled(tv_id, body.enabled)
    if body.name is not None:
        await storage.tvs.rename(tv_id, body.name)
    await supervisor.refresh(tv_id)
    return tv_out(
        await existing_tv(storage, tv_id), supervisor.status(tv_id), supervisor.plan_limited(tv_id)
    )


@router.delete("/{tv_id}", status_code=204, responses=NOT_FOUND_ERRORS)
async def remove_tv(
    tv_id: str, _: CanAdmin, storage: StorageDep, supervisor: SupervisorDep
) -> Response:
    if not await storage.tvs.remove(tv_id):
        raise not_found("TV")
    await supervisor.refresh()
    return Response(status_code=204)
