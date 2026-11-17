"""Engine-wide settings: the language of on-screen messages and the household time zone."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends

from tvbalance.api.deps import CanAdmin, CanRead, get_storage
from tvbalance.api.schemas.errors import AUTH_ERRORS
from tvbalance.api.schemas.settings import Language, SettingsOut, SettingsUpdate
from tvbalance.app.messages import DEFAULT_LANGUAGE
from tvbalance.ports.storage import Storage

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

StorageDep = Annotated[Storage, Depends(get_storage)]


async def _current(storage: Storage) -> SettingsOut:
    language = str(await storage.settings.get("language", DEFAULT_LANGUAGE))
    timezone = await storage.settings.get("timezone")
    return SettingsOut(language=cast(Language, language), timezone=timezone or None)


@router.get("", response_model=SettingsOut, responses=AUTH_ERRORS)
async def read_settings(_: CanRead, storage: StorageDep) -> SettingsOut:
    return await _current(storage)


@router.put("", response_model=SettingsOut, responses=AUTH_ERRORS)
async def change_settings(body: SettingsUpdate, _: CanAdmin, storage: StorageDep) -> SettingsOut:
    if body.language is not None:
        await storage.settings.set("language", body.language)
    if "timezone" in body.model_fields_set:
        await storage.settings.set("timezone", body.timezone)
    return await _current(storage)
