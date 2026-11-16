from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text
from sqlalchemy.exc import StatementError

from tvbalance.infra.db.engine import create_engine
from tvbalance.infra.db.types import UtcDateTime

events = Table("t", MetaData(), Column("id", Integer, primary_key=True), Column("at", UtcDateTime))


async def test_every_connection_gets_the_pragmas(tmp_path: Path) -> None:
    engine = create_engine(tmp_path / "test.db")
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("PRAGMA journal_mode"))).scalar() == "wal"
            assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
            assert (await conn.execute(text("PRAGMA busy_timeout"))).scalar() == 5000
    finally:
        await engine.dispose()


async def test_aware_datetimes_come_back_as_the_same_instant_in_utc(tmp_path: Path) -> None:
    engine = create_engine(tmp_path / "test.db")
    plus_two = timezone(timedelta(hours=2))
    moment = datetime(2026, 11, 16, 20, 30, tzinfo=plus_two)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(events.metadata.create_all)
            await conn.execute(insert(events).values(id=1, at=moment))
            stored = (await conn.execute(select(events.c.at))).scalar_one()
    finally:
        await engine.dispose()
    assert stored == moment
    assert stored.tzinfo is UTC
    assert stored.hour == 18


async def test_naive_datetimes_are_rejected(tmp_path: Path) -> None:
    engine = create_engine(tmp_path / "test.db")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(events.metadata.create_all)
            with pytest.raises(StatementError, match="naive"):
                await conn.execute(insert(events).values(id=1, at=datetime(2026, 11, 16, 20, 30)))
    finally:
        await engine.dispose()


async def test_null_stays_null(tmp_path: Path) -> None:
    engine = create_engine(tmp_path / "test.db")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(events.metadata.create_all)
            await conn.execute(insert(events).values(id=1, at=None))
            assert (await conn.execute(select(events.c.at))).scalar_one() is None
    finally:
        await engine.dispose()
