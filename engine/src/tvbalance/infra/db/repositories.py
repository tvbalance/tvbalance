"""SQLite implementations of the storage ports, and ``open_storage`` to assemble them."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import Row, delete, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from tvbalance.config import EngineConfig
from tvbalance.domain.models import Override, Policy, Usage
from tvbalance.infra.clock import SystemClock
from tvbalance.infra.db import tables
from tvbalance.infra.db.engine import create_engine
from tvbalance.infra.db.migrate import upgrade_to_head
from tvbalance.infra.db.policy_codec import VERSION, decode_policy, encode_policy
from tvbalance.infra.secrets import SecretBox, SecretError
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import NotFoundError, PolicyRecord, StoredEvent, TvRecord

DB_FILE = "tvbalance.db"
KEY_FILE = "secret.key"


@contextmanager
def _unknown_references() -> Iterator[None]:
    """A foreign key that points nowhere means the TV or policy does not exist."""
    try:
        yield
    except IntegrityError as ex:
        if "FOREIGN KEY" in str(ex.orig):
            raise NotFoundError("the referenced TV or policy does not exist") from ex
        raise


class SqliteTvStore:
    def __init__(self, engine: AsyncEngine, box: SecretBox, clock: Clock) -> None:
        self._engine, self._box, self._clock = engine, box, clock

    async def add(
        self,
        adapter_id: str,
        name: str,
        host: str,
        credentials: dict[str, str],
        policy_id: int | None = None,
    ) -> TvRecord:
        tv_id, now = str(uuid.uuid4()), self._clock.now()
        with _unknown_references():
            async with self._engine.begin() as conn:
                await conn.execute(
                    tables.tvs.insert().values(
                        id=tv_id,
                        adapter_id=adapter_id,
                        name=name,
                        host=host,
                        credentials_enc=self._box.seal_json(credentials),
                        policy_id=policy_id,
                        enabled=True,
                        created_at=now,
                    )
                )
        return TvRecord(tv_id, adapter_id, name, host, dict(credentials), policy_id, True, now)

    async def get(self, tv_id: str) -> TvRecord | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(select(tables.tvs).where(tables.tvs.c.id == tv_id))).first()
        return None if row is None else self._record(row)

    async def list(self) -> list[TvRecord]:
        query = select(tables.tvs).order_by(tables.tvs.c.created_at, tables.tvs.c.id)
        async with self._engine.connect() as conn:
            return [self._record(row) for row in await conn.execute(query)]

    async def update_credentials(self, tv_id: str, credentials: dict[str, str]) -> None:
        await self._update(tv_id, credentials_enc=self._box.seal_json(credentials))

    async def assign_policy(self, tv_id: str, policy_id: int | None) -> None:
        await self._update(tv_id, policy_id=policy_id)

    async def remove(self, tv_id: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(delete(tables.tvs).where(tables.tvs.c.id == tv_id))
        return result.rowcount > 0

    async def _update(self, tv_id: str, **values: Any) -> None:
        with _unknown_references():
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    update(tables.tvs).where(tables.tvs.c.id == tv_id).values(**values)
                )
        if result.rowcount == 0:
            raise NotFoundError(f"no TV {tv_id!r}")

    def _record(self, row: Row[Any]) -> TvRecord:
        try:
            credentials, needs_pairing = self._box.open_json(row.credentials_enc), False
        except SecretError:
            credentials, needs_pairing = {}, True
        return TvRecord(
            row.id,
            row.adapter_id,
            row.name,
            row.host,
            credentials,
            row.policy_id,
            row.enabled,
            row.created_at,
            needs_pairing,
        )


class SqlitePolicyStore:
    def __init__(self, engine: AsyncEngine, clock: Clock) -> None:
        self._engine, self._clock = engine, clock

    async def create(self, name: str, policy: Policy) -> int:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                tables.policies.insert().values(
                    name=name,
                    version=VERSION,
                    document=encode_policy(policy),
                    updated_at=self._clock.now(),
                )
            )
        primary_key = result.inserted_primary_key
        assert primary_key is not None  # a plain INSERT always reports its key
        return int(primary_key[0])

    async def get(self, policy_id: int) -> PolicyRecord | None:
        query = select(tables.policies).where(tables.policies.c.id == policy_id)
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        return None if row is None else _policy_record(row)

    async def save(self, policy_id: int, policy: Policy, name: str | None = None) -> None:
        values: dict[str, Any] = {
            "version": VERSION,
            "document": encode_policy(policy),
            "updated_at": self._clock.now(),
        }
        if name is not None:
            values["name"] = name
        async with self._engine.begin() as conn:
            result = await conn.execute(
                update(tables.policies).where(tables.policies.c.id == policy_id).values(**values)
            )
        if result.rowcount == 0:
            raise NotFoundError(f"no policy {policy_id}")

    async def list(self) -> list[PolicyRecord]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(select(tables.policies).order_by(tables.policies.c.id))
            return [_policy_record(row) for row in rows]


def _policy_record(row: Row[Any]) -> PolicyRecord:
    return PolicyRecord(row.id, row.name, decode_policy(row.document), row.updated_at)


class SqliteUsageStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get(self, tv_id: str, day: date) -> Usage:
        query = select(tables.usage).where(tables.usage.c.tv_id == tv_id, tables.usage.c.day == day)
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        return Usage(day) if row is None else Usage(day, row.watched_seconds, row.bonus_minutes)

    async def add_watched(self, tv_id: str, day: date, seconds: int) -> None:
        await self._add(tv_id, day, watched_seconds=seconds, bonus_minutes=0)

    async def add_bonus(self, tv_id: str, day: date, minutes: int) -> None:
        await self._add(tv_id, day, watched_seconds=0, bonus_minutes=minutes)

    async def _add(
        self, tv_id: str, day: date, *, watched_seconds: int, bonus_minutes: int
    ) -> None:
        """One atomic upsert, so concurrent callers never overwrite each other's increment."""
        stmt = insert(tables.usage).values(
            tv_id=tv_id, day=day, watched_seconds=watched_seconds, bonus_minutes=bonus_minutes
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[tables.usage.c.tv_id, tables.usage.c.day],
            set_={
                "watched_seconds": tables.usage.c.watched_seconds + stmt.excluded.watched_seconds,
                "bonus_minutes": tables.usage.c.bonus_minutes + stmt.excluded.bonus_minutes,
            },
        )
        with _unknown_references():
            async with self._engine.begin() as conn:
                await conn.execute(stmt)


class SqliteOverrideStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add(self, tv_id: str, override: Override) -> None:
        with _unknown_references():
            async with self._engine.begin() as conn:
                await conn.execute(
                    tables.overrides.insert().values(
                        tv_id=tv_id,
                        allow=override.allow,
                        until=override.until,
                        created_at=override.created_at,
                    )
                )

    async def active(self, tv_id: str, now: datetime) -> tuple[Override, ...]:
        query = (
            select(tables.overrides)
            .where(tables.overrides.c.tv_id == tv_id, tables.overrides.c.until > now)
            .order_by(tables.overrides.c.created_at, tables.overrides.c.id)
        )
        async with self._engine.connect() as conn:
            rows = await conn.execute(query)
            return tuple(Override(r.allow, r.until, r.created_at) for r in rows)

    async def clear(self, tv_id: str) -> int:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                delete(tables.overrides).where(tables.overrides.c.tv_id == tv_id)
            )
        return result.rowcount


class SqliteEventLog:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def append(
        self, tv_id: str | None, event_type: str, payload: dict[str, Any], at: datetime
    ) -> None:
        with _unknown_references():
            async with self._engine.begin() as conn:
                await conn.execute(
                    tables.events.insert().values(
                        tv_id=tv_id, occurred_at=at, type=event_type, payload=payload
                    )
                )

    async def recent(
        self, tv_id: str | None, since: datetime, limit: int = 100
    ) -> list[StoredEvent]:
        query = select(tables.events).where(tables.events.c.occurred_at >= since)
        if tv_id is not None:
            query = query.where(tables.events.c.tv_id == tv_id)
        query = query.order_by(tables.events.c.occurred_at.desc(), tables.events.c.id.desc())
        async with self._engine.connect() as conn:
            rows = await conn.execute(query.limit(limit))
            return [StoredEvent(r.id, r.tv_id, r.occurred_at, r.type, r.payload) for r in rows]


class SqliteSettingsStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get(self, key: str, default: Any = None) -> Any:
        query = select(tables.settings.c.value).where(tables.settings.c.key == key)
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        return default if row is None else row.value

    async def set(self, key: str, value: Any) -> None:
        stmt = insert(tables.settings).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=[tables.settings.c.key], set_={"value": stmt.excluded.value}
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)


class SqliteStorage:
    def __init__(self, engine: AsyncEngine, box: SecretBox, clock: Clock) -> None:
        self._engine = engine
        self.tvs = SqliteTvStore(engine, box, clock)
        self.policies = SqlitePolicyStore(engine, clock)
        self.usage = SqliteUsageStore(engine)
        self.overrides = SqliteOverrideStore(engine)
        self.events = SqliteEventLog(engine)
        self.settings = SqliteSettingsStore(engine)

    async def close(self) -> None:
        await self._engine.dispose()


async def open_storage(config: EngineConfig, clock: Clock | None = None) -> SqliteStorage:
    """Open (creating it when needed) the data directory and bring the schema up to date."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(config.data_dir / DB_FILE)
    try:
        await upgrade_to_head(engine)
        box = SecretBox.load_or_create(config.data_dir / KEY_FILE)
    except BaseException:
        await engine.dispose()
        raise
    return SqliteStorage(engine, box, clock or SystemClock())
