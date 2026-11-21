"""SQLite implementations of the storage ports, and ``open_storage`` to assemble them."""

from __future__ import annotations

import base64
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnClause, Row, delete, literal_column, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from tvbalance.config import EngineConfig
from tvbalance.domain.enforcement import EnforcementState
from tvbalance.domain.models import Override, Policy, Usage
from tvbalance.infra.clock import SystemClock
from tvbalance.infra.db import tables
from tvbalance.infra.db.engine import create_engine
from tvbalance.infra.db.migrate import upgrade_to_head
from tvbalance.infra.db.policy_codec import VERSION, decode_policy, encode_policy
from tvbalance.infra.db.state_codec import StateDecodeError, decode_state, encode_state
from tvbalance.infra.secrets import SecretBox, SecretError
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import (
    AdminRecord,
    ApiTokenRecord,
    NotFoundError,
    PolicyRecord,
    PushSubscriptionRecord,
    SessionRecord,
    StoredEvent,
    TvRecord,
)

log = logging.getLogger(__name__)

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

    async def set_enabled(self, tv_id: str, enabled: bool) -> None:
        await self._update(tv_id, enabled=enabled)

    async def rename(self, tv_id: str, name: str) -> None:
        await self._update(tv_id, name=name)

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


_SECRET_PREFIX = "secret:"


class SqliteSecretSettingsStore:
    """Secrets sit in the settings table under a ``secret:`` key, sealed and base64 encoded."""

    def __init__(self, settings: SqliteSettingsStore, box: SecretBox) -> None:
        self._settings, self._box = settings, box

    async def get(self, key: str) -> str | None:
        stored = await self._settings.get(_SECRET_PREFIX + key)
        if not isinstance(stored, str):
            return None
        try:
            return self._box.decrypt(base64.b64decode(stored, validate=True)).decode()
        except (SecretError, ValueError):
            return None

    async def set(self, key: str, value: str) -> None:
        sealed = self._box.encrypt(value.encode())
        await self._settings.set(_SECRET_PREFIX + key, base64.b64encode(sealed).decode("ascii"))


class SqliteEnforcementStateStore:
    def __init__(self, engine: AsyncEngine, clock: Clock) -> None:
        self._engine, self._clock = engine, clock

    async def load(self, tv_id: str) -> EnforcementState:
        query = select(tables.enforcement_state.c.state).where(
            tables.enforcement_state.c.tv_id == tv_id
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        if row is None:
            return EnforcementState()
        try:
            return decode_state(row.state)
        except StateDecodeError:
            log.warning("unreadable enforcement state for TV %s: starting fresh", tv_id)
            return EnforcementState()

    async def save(self, tv_id: str, state: EnforcementState) -> None:
        values = {"state": encode_state(state), "updated_at": self._clock.now()}
        stmt = insert(tables.enforcement_state).values(tv_id=tv_id, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[tables.enforcement_state.c.tv_id], set_=values
        )
        with _unknown_references():
            async with self._engine.begin() as conn:
                await conn.execute(stmt)


ADMIN_ID = 1
_INSERTION_ORDER: ColumnClause[Any] = literal_column(
    "rowid"
)  # ties on created_at keep the order of insertion


class SqliteAuthStore:
    def __init__(self, engine: AsyncEngine, clock: Clock) -> None:
        self._engine, self._clock = engine, clock

    async def get_admin(self) -> AdminRecord | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(select(tables.admin))).first()
        if row is None:
            return None
        return AdminRecord(row.password_hash, row.pin_hash, row.pin_failures, row.updated_at)

    async def create_admin(self, password_hash: str) -> bool:
        try:
            async with self._engine.begin() as conn:
                await conn.execute(
                    tables.admin.insert().values(
                        id=ADMIN_ID,
                        password_hash=password_hash,
                        pin_hash=None,
                        pin_failures=0,
                        updated_at=self._clock.now(),
                    )
                )
        except IntegrityError:
            return False
        return True

    async def set_password_hash(self, password_hash: str) -> None:
        await self._update_admin(password_hash=password_hash)

    async def set_pin_hash(self, pin_hash: str | None) -> None:
        await self._update_admin(pin_hash=pin_hash, pin_failures=0)

    async def record_pin_failure(self) -> int:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(tables.admin).values(pin_failures=tables.admin.c.pin_failures + 1)
            )
            failures = (await conn.execute(select(tables.admin.c.pin_failures))).scalar()
        return failures or 0

    async def reset_pin_failures(self) -> None:
        await self._update_admin(pin_failures=0)

    async def _update_admin(self, **values: Any) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(update(tables.admin).values(updated_at=self._clock.now(), **values))

    async def add_session(
        self, token_hash: str, kind: str, expires_at: datetime, user_agent: str
    ) -> SessionRecord:
        now = self._clock.now()
        record = SessionRecord(uuid.uuid4().hex, kind, now, now, expires_at, user_agent)
        async with self._engine.begin() as conn:
            await conn.execute(
                tables.sessions.insert().values(
                    id=record.id,
                    token_hash=token_hash,
                    kind=kind,
                    created_at=now,
                    last_seen_at=now,
                    expires_at=expires_at,
                    user_agent=user_agent,
                )
            )
        return record

    async def get_session(self, token_hash: str) -> SessionRecord | None:
        query = select(tables.sessions).where(tables.sessions.c.token_hash == token_hash)
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        return None if row is None else _session_record(row)

    async def touch_session(
        self, session_id: str, last_seen_at: datetime, expires_at: datetime
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(tables.sessions)
                .where(tables.sessions.c.id == session_id)
                .values(last_seen_at=last_seen_at, expires_at=expires_at)
            )

    async def list_sessions(self) -> list[SessionRecord]:
        query = select(tables.sessions).order_by(tables.sessions.c.created_at, _INSERTION_ORDER)
        async with self._engine.connect() as conn:
            return [_session_record(r) for r in await conn.execute(query)]

    async def revoke_session(self, session_id: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                delete(tables.sessions).where(tables.sessions.c.id == session_id)
            )
        return result.rowcount > 0

    async def revoke_all_sessions(self, except_id: str | None = None) -> int:
        stmt = delete(tables.sessions)
        if except_id is not None:
            stmt = stmt.where(tables.sessions.c.id != except_id)
        async with self._engine.begin() as conn:
            return (await conn.execute(stmt)).rowcount

    async def purge_expired_sessions(self, now: datetime) -> int:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                delete(tables.sessions).where(tables.sessions.c.expires_at <= now)
            )
        return result.rowcount

    async def add_token(self, name: str, token_hash: str, scopes: frozenset[str]) -> ApiTokenRecord:
        now = self._clock.now()
        record = ApiTokenRecord(uuid.uuid4().hex, name, scopes, now, None, None)
        async with self._engine.begin() as conn:
            await conn.execute(
                tables.api_tokens.insert().values(
                    id=record.id,
                    name=name,
                    token_hash=token_hash,
                    scopes=sorted(scopes),
                    created_at=now,
                )
            )
        return record

    async def get_token(self, token_hash: str) -> ApiTokenRecord | None:
        query = select(tables.api_tokens).where(
            tables.api_tokens.c.token_hash == token_hash,
            tables.api_tokens.c.revoked_at.is_(None),
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(query)).first()
        return None if row is None else _token_record(row)

    async def touch_token(self, token_id: str, used_at: datetime) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(tables.api_tokens)
                .where(tables.api_tokens.c.id == token_id)
                .values(last_used_at=used_at)
            )

    async def list_tokens(self) -> list[ApiTokenRecord]:
        query = select(tables.api_tokens).order_by(tables.api_tokens.c.created_at, _INSERTION_ORDER)
        async with self._engine.connect() as conn:
            return [_token_record(r) for r in await conn.execute(query)]

    async def revoke_token(self, token_id: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                update(tables.api_tokens)
                .where(tables.api_tokens.c.id == token_id, tables.api_tokens.c.revoked_at.is_(None))
                .values(revoked_at=self._clock.now())
            )
        return result.rowcount > 0


def _session_record(row: Row[Any]) -> SessionRecord:
    return SessionRecord(
        row.id, row.kind, row.created_at, row.last_seen_at, row.expires_at, row.user_agent
    )


def _token_record(row: Row[Any]) -> ApiTokenRecord:
    return ApiTokenRecord(
        row.id, row.name, frozenset(row.scopes), row.created_at, row.last_used_at, row.revoked_at
    )


class SqlitePushSubscriptionStore:
    def __init__(self, engine: AsyncEngine, box: SecretBox, clock: Clock) -> None:
        self._engine, self._box, self._clock = engine, box, clock

    def _record(self, row: Row[Any]) -> PushSubscriptionRecord:
        return PushSubscriptionRecord(
            id=row.id,
            endpoint=row.endpoint,
            p256dh=row.p256dh,
            auth=self._box.decrypt(row.auth_sealed).decode(),
            events=frozenset(row.events),
            language=row.language,
            app_url=row.app_url,
            user_agent=row.user_agent,
            created_at=row.created_at,
            last_sent_at=row.last_sent_at,
            failures=row.failures,
        )

    async def upsert(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        events: frozenset[str],
        language: str,
        app_url: str,
        user_agent: str,
    ) -> tuple[PushSubscriptionRecord, bool]:
        table = tables.push_subscriptions
        values = {
            "p256dh": p256dh,
            "auth_sealed": self._box.encrypt(auth.encode()),
            "events": sorted(events),
            "language": language,
            "app_url": app_url,
            "user_agent": user_agent,
            "failures": 0,
        }
        async with self._engine.begin() as conn:
            existing = (
                await conn.execute(select(table.c.id).where(table.c.endpoint == endpoint))
            ).scalar()
            created = existing is None
            subscription_id = existing or uuid.uuid4().hex
            if created:
                await conn.execute(
                    table.insert().values(
                        id=subscription_id,
                        endpoint=endpoint,
                        created_at=self._clock.now(),
                        last_sent_at=None,
                        **values,
                    )
                )
            else:
                await conn.execute(
                    update(table).where(table.c.id == subscription_id).values(**values)
                )
            row = (await conn.execute(select(table).where(table.c.id == subscription_id))).one()
        return self._record(row), created

    async def list(self) -> list[PushSubscriptionRecord]:
        table = tables.push_subscriptions
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(select(table).order_by(table.c.created_at, table.c.id))
            ).all()
        return [self._record(row) for row in rows]

    async def get(self, subscription_id: str) -> PushSubscriptionRecord | None:
        table = tables.push_subscriptions
        async with self._engine.connect() as conn:
            row = (await conn.execute(select(table).where(table.c.id == subscription_id))).first()
        return None if row is None else self._record(row)

    async def update_events(self, subscription_id: str, events: frozenset[str]) -> bool:
        table = tables.push_subscriptions
        async with self._engine.begin() as conn:
            result = await conn.execute(
                update(table).where(table.c.id == subscription_id).values(events=sorted(events))
            )
        return result.rowcount > 0

    async def delete(self, subscription_id: str) -> bool:
        table = tables.push_subscriptions
        async with self._engine.begin() as conn:
            result = await conn.execute(delete(table).where(table.c.id == subscription_id))
        return result.rowcount > 0

    async def record_delivery(self, subscription_id: str) -> None:
        table = tables.push_subscriptions
        async with self._engine.begin() as conn:
            await conn.execute(
                update(table)
                .where(table.c.id == subscription_id)
                .values(last_sent_at=self._clock.now(), failures=0)
            )

    async def record_failure(self, subscription_id: str) -> int:
        table = tables.push_subscriptions
        async with self._engine.begin() as conn:
            await conn.execute(
                update(table)
                .where(table.c.id == subscription_id)
                .values(failures=table.c.failures + 1)
            )
            failures = (
                await conn.execute(select(table.c.failures).where(table.c.id == subscription_id))
            ).scalar()
        return failures or 0


class SqliteStorage:
    def __init__(self, engine: AsyncEngine, box: SecretBox, clock: Clock) -> None:
        self._engine = engine
        self.tvs = SqliteTvStore(engine, box, clock)
        self.policies = SqlitePolicyStore(engine, clock)
        self.usage = SqliteUsageStore(engine)
        self.overrides = SqliteOverrideStore(engine)
        self.events = SqliteEventLog(engine)
        self.settings = SqliteSettingsStore(engine)
        self.secrets = SqliteSecretSettingsStore(self.settings, box)
        self.enforcement = SqliteEnforcementStateStore(engine, clock)
        self.auth = SqliteAuthStore(engine, clock)
        self.push = SqlitePushSubscriptionStore(engine, box, clock)

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
