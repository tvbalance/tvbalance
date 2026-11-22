from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tvbalance.config import EngineConfig
from tvbalance.domain.models import ContentKey
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import NotFoundError, Storage

DAY = date(2026, 11, 16)
YOUTUBE = ContentKey("app", "youtube")
HDMI = ContentKey("input", "HDMI_1")


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 16, 20, 0, tzinfo=UTC)


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FixedClock())
    yield store
    await store.close()


async def add_tv(storage: Storage) -> str:
    return (await storage.tvs.add("fake", "Living room", "tv.local", {"client_key": "k"})).id


async def test_a_day_without_viewing_is_empty(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    assert await storage.content_usage.day(tv_id, DAY) == {}


async def test_increments_accumulate_per_content(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await storage.content_usage.add(tv_id, DAY, YOUTUBE, 30)
    await storage.content_usage.add(tv_id, DAY, YOUTUBE, 20)
    await storage.content_usage.add(tv_id, DAY, HDMI, 5)
    assert await storage.content_usage.day(tv_id, DAY) == {YOUTUBE: 50, HDMI: 5}


async def test_a_range_sums_the_days_inclusive(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    for offset, seconds in enumerate((10, 20, 40)):
        await storage.content_usage.add(tv_id, date(2026, 11, 15 + offset), YOUTUBE, seconds)
    assert await storage.content_usage.between(tv_id, date(2026, 11, 15), date(2026, 11, 16)) == {
        YOUTUBE: 30
    }


async def test_an_unknown_tv_is_rejected(storage: Storage) -> None:
    with pytest.raises(NotFoundError):
        await storage.content_usage.add("nope", DAY, YOUTUBE, 1)


async def test_deleting_a_tv_removes_its_content_usage(storage: Storage) -> None:
    tv_id = await add_tv(storage)
    await storage.content_usage.add(tv_id, DAY, YOUTUBE, 30)
    await storage.tvs.remove(tv_id)
    assert await storage.content_usage.day(tv_id, DAY) == {}
