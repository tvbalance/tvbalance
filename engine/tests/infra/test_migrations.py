from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from tvbalance.infra.db.engine import create_engine
from tvbalance.infra.db.migrate import alembic_config, upgrade_to_head
from tvbalance.infra.db.tables import metadata

TABLES = {"policies", "tvs", "usage", "overrides", "events", "settings", "enforcement_state"}


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(tmp_path / "migrations.db")
    yield engine
    await engine.dispose()


def _table_names(conn: Connection) -> set[str]:
    return set(inspect(conn).get_table_names()) - {"alembic_version"}


def _drift(conn: Connection) -> list[object]:
    return compare_metadata(MigrationContext.configure(conn), metadata)


def _downgrade_to_base(conn: Connection) -> None:
    config = alembic_config()
    config.attributes["connection"] = conn
    command.downgrade(config, "base")


async def test_upgrade_on_an_empty_database_creates_the_schema(engine: AsyncEngine) -> None:
    await upgrade_to_head(engine)
    async with engine.connect() as conn:
        assert await conn.run_sync(_table_names) == TABLES
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    assert version == "0002"


async def test_the_migrations_and_the_table_definitions_agree(engine: AsyncEngine) -> None:
    await upgrade_to_head(engine)
    async with engine.connect() as conn:
        assert await conn.run_sync(_drift) == []


async def test_upgrading_twice_is_harmless(engine: AsyncEngine) -> None:
    await upgrade_to_head(engine)
    await upgrade_to_head(engine)
    async with engine.connect() as conn:
        assert await conn.run_sync(_table_names) == TABLES


async def test_downgrade_to_base_then_upgrade_again(engine: AsyncEngine) -> None:
    await upgrade_to_head(engine)
    async with engine.begin() as conn:
        await conn.run_sync(_downgrade_to_base)
    async with engine.connect() as conn:
        assert await conn.run_sync(_table_names) == set()
    await upgrade_to_head(engine)
    async with engine.connect() as conn:
        assert await conn.run_sync(_table_names) == TABLES
        assert await conn.run_sync(_drift) == []


async def test_existing_data_survives_a_repeated_upgrade(engine: AsyncEngine) -> None:
    await upgrade_to_head(engine)
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO settings (key, value) VALUES ('language', '\"it\"')"))
    await upgrade_to_head(engine)
    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT key, value FROM settings"))).all()
    assert [tuple(r) for r in rows] == [("language", '"it"')]
