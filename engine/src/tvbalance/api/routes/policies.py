"""Policies: what a TV may show and when. Saving one restarts the TVs that use it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from tvbalance.api.deps import CanAdmin, CanRead, get_storage, get_supervisor
from tvbalance.api.errors import ApiError, not_found
from tvbalance.api.schemas.errors import AUTH_ERRORS, NOT_FOUND_ERRORS
from tvbalance.api.schemas.policies import PolicyCreate, PolicyDoc, PolicyOut, PolicyUpdate
from tvbalance.app.supervisor import Supervisor
from tvbalance.domain.models import Policy
from tvbalance.domain.validation import validate_policy
from tvbalance.infra.db.policy_codec import PolicyDecodeError, decode_policy, encode_policy
from tvbalance.ports.storage import PolicyRecord, Storage

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])

StorageDep = Annotated[Storage, Depends(get_storage)]
SupervisorDep = Annotated[Supervisor, Depends(get_supervisor)]


def to_domain(doc: PolicyDoc) -> Policy:
    """The checked policy, or a 422 that names every problem found."""
    try:
        policy = decode_policy({"version": 1, **doc.model_dump(mode="json")})
    except PolicyDecodeError as ex:
        raise ApiError(422, "validation_failed", str(ex)) from ex
    if issues := validate_policy(policy):
        raise ApiError(
            422,
            "validation_failed",
            "the policy is inconsistent",
            details=[{"code": i.code.value, "detail": i.detail} for i in issues],
        )
    return policy


def to_doc(policy: Policy) -> PolicyDoc:
    document = {k: v for k, v in encode_policy(policy).items() if k != "version"}
    return PolicyDoc.model_validate(document)


async def _out(record: PolicyRecord, storage: Storage) -> PolicyOut:
    tv_ids = [t.id for t in await storage.tvs.list() if t.policy_id == record.id]
    return PolicyOut(
        id=record.id,
        name=record.name,
        policy=to_doc(record.policy),
        updated_at=record.updated_at,
        tv_ids=tv_ids,
    )


async def _existing(storage: Storage, policy_id: int) -> PolicyRecord:
    record = await storage.policies.get(policy_id)
    if record is None:
        raise not_found("policy")
    return record


@router.get("", response_model=list[PolicyOut], responses=AUTH_ERRORS)
async def list_policies(_: CanRead, storage: StorageDep) -> list[PolicyOut]:
    return [await _out(r, storage) for r in await storage.policies.list()]


@router.get("/{policy_id}", response_model=PolicyOut, responses=NOT_FOUND_ERRORS)
async def get_policy(policy_id: int, _: CanRead, storage: StorageDep) -> PolicyOut:
    return await _out(await _existing(storage, policy_id), storage)


@router.post("", response_model=PolicyOut, status_code=201, responses=AUTH_ERRORS)
async def create_policy(body: PolicyCreate, _: CanAdmin, storage: StorageDep) -> PolicyOut:
    policy_id = await storage.policies.create(body.name, to_domain(body.policy))
    return await _out(await _existing(storage, policy_id), storage)


@router.put("/{policy_id}", response_model=PolicyOut, responses=NOT_FOUND_ERRORS)
async def save_policy(
    policy_id: int, body: PolicyUpdate, _: CanAdmin, storage: StorageDep, supervisor: SupervisorDep
) -> PolicyOut:
    await _existing(storage, policy_id)
    await storage.policies.save(policy_id, to_domain(body.policy), body.name)
    for tv in await storage.tvs.list():
        if tv.policy_id == policy_id:
            await supervisor.refresh(tv.id)
    return await _out(await _existing(storage, policy_id), storage)
