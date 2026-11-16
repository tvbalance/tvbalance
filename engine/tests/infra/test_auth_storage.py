from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage

T0 = datetime(2026, 11, 17, 20, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


class FixedClock:
    def __init__(self) -> None:
        self.current = T0

    def now(self) -> datetime:
        return self.current


@pytest.fixture
async def storage(tmp_path: Path) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), FixedClock())
    yield store
    await store.close()


async def test_there_is_no_admin_before_setup(storage: Storage) -> None:
    assert await storage.auth.get_admin() is None


async def test_the_admin_can_be_created_only_once(storage: Storage) -> None:
    assert await storage.auth.create_admin("hash-1") is True
    assert await storage.auth.create_admin("hash-2") is False
    admin = await storage.auth.get_admin()
    assert admin is not None
    assert admin.password_hash == "hash-1"
    assert admin.pin_hash is None
    assert admin.pin_failures == 0
    assert admin.updated_at == T0


async def test_the_password_hash_is_replaced(storage: Storage) -> None:
    await storage.auth.create_admin("old")
    await storage.auth.set_password_hash("new")
    admin = await storage.auth.get_admin()
    assert admin is not None and admin.password_hash == "new"


async def test_secrets_stay_out_of_the_repr(storage: Storage) -> None:
    await storage.auth.create_admin("super-secret-hash")
    admin = await storage.auth.get_admin()
    assert "super-secret-hash" not in repr(admin)


async def test_the_pin_is_set_counted_and_cleared(storage: Storage) -> None:
    await storage.auth.create_admin("hash")
    await storage.auth.set_pin_hash("pin-hash")
    assert await storage.auth.record_pin_failure() == 1
    assert await storage.auth.record_pin_failure() == 2
    admin = await storage.auth.get_admin()
    assert admin is not None and admin.pin_hash == "pin-hash" and admin.pin_failures == 2

    await storage.auth.reset_pin_failures()
    admin = await storage.auth.get_admin()
    assert admin is not None and admin.pin_failures == 0

    await storage.auth.record_pin_failure()
    await storage.auth.set_pin_hash(None)  # a new or removed PIN starts clean
    admin = await storage.auth.get_admin()
    assert admin is not None and admin.pin_hash is None and admin.pin_failures == 0


async def test_a_session_is_found_by_the_hash_of_its_token(storage: Storage) -> None:
    created = await storage.auth.add_session("h1", "admin", T0 + HOUR, "Firefox")
    found = await storage.auth.get_session("h1")
    assert found == created
    assert found.kind == "admin" and found.user_agent == "Firefox"
    assert found.created_at == found.last_seen_at == T0
    assert found.expires_at == T0 + HOUR
    assert await storage.auth.get_session("other") is None


async def test_touching_a_session_slides_its_expiry(storage: Storage) -> None:
    session = await storage.auth.add_session("h1", "admin", T0 + HOUR, "")
    later = T0 + 30 * timedelta(minutes=1)
    await storage.auth.touch_session(session.id, later, later + HOUR)
    found = await storage.auth.get_session("h1")
    assert found is not None
    assert found.last_seen_at == later and found.expires_at == later + HOUR


async def test_sessions_are_listed_oldest_first_and_revoked_one_by_one(storage: Storage) -> None:
    first = await storage.auth.add_session("h1", "admin", T0 + HOUR, "")
    second = await storage.auth.add_session("h2", "pin", T0 + HOUR, "")
    assert [s.id for s in await storage.auth.list_sessions()] == [first.id, second.id]

    assert await storage.auth.revoke_session(first.id) is True
    assert await storage.auth.revoke_session(first.id) is False
    assert await storage.auth.get_session("h1") is None
    assert [s.id for s in await storage.auth.list_sessions()] == [second.id]


async def test_all_sessions_can_be_revoked_except_one(storage: Storage) -> None:
    keep = await storage.auth.add_session("h1", "admin", T0 + HOUR, "")
    await storage.auth.add_session("h2", "admin", T0 + HOUR, "")
    await storage.auth.add_session("h3", "pin", T0 + HOUR, "")
    assert await storage.auth.revoke_all_sessions(except_id=keep.id) == 2
    assert [s.id for s in await storage.auth.list_sessions()] == [keep.id]
    assert await storage.auth.revoke_all_sessions() == 1
    assert await storage.auth.list_sessions() == []


async def test_expired_sessions_are_purged(storage: Storage) -> None:
    await storage.auth.add_session("old", "admin", T0 - HOUR, "")
    live = await storage.auth.add_session("live", "admin", T0 + HOUR, "")
    assert await storage.auth.purge_expired_sessions(T0) == 1
    assert [s.id for s in await storage.auth.list_sessions()] == [live.id]


async def test_a_token_is_found_by_its_hash_with_its_scopes(storage: Storage) -> None:
    created = await storage.auth.add_token("Home Assistant", "t1", frozenset({"read", "control"}))
    found = await storage.auth.get_token("t1")
    assert found == created
    assert found.name == "Home Assistant"
    assert found.scopes == frozenset({"read", "control"})
    assert found.created_at == T0
    assert found.last_used_at is None and found.revoked_at is None
    assert await storage.auth.get_token("other") is None


async def test_using_a_token_records_the_time(storage: Storage) -> None:
    token = await storage.auth.add_token("HA", "t1", frozenset({"read"}))
    await storage.auth.touch_token(token.id, T0 + HOUR)
    found = await storage.auth.get_token("t1")
    assert found is not None and found.last_used_at == T0 + HOUR


async def test_a_revoked_token_stops_working_but_stays_listed(storage: Storage) -> None:
    token = await storage.auth.add_token("HA", "t1", frozenset({"read"}))
    assert await storage.auth.revoke_token(token.id) is True
    assert await storage.auth.revoke_token(token.id) is False
    assert await storage.auth.get_token("t1") is None
    listed = await storage.auth.list_tokens()
    assert [t.id for t in listed] == [token.id]
    assert listed[0].revoked_at == T0


async def test_unknown_ids_are_not_found(storage: Storage) -> None:
    assert await storage.auth.revoke_session("nope") is False
    assert await storage.auth.revoke_token("nope") is False
