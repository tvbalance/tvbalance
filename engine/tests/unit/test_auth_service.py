from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from support import FakeClock

from tvbalance.app.auth import (
    AlreadySetUp,
    AuthService,
    InvalidCredentials,
    PinLocked,
    RateLimited,
    SetupRequired,
    WeakSecret,
    hash_token,
)
from tvbalance.config import EngineConfig
from tvbalance.infra.db.repositories import open_storage
from tvbalance.ports.storage import Storage

PASSWORD = "correct horse battery"
PIN = "4821"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def storage(tmp_path: Path, clock: FakeClock) -> AsyncIterator[Storage]:
    store = await open_storage(EngineConfig(data_dir=tmp_path / "data"), clock)
    yield store
    await store.close()


@pytest.fixture
def auth(storage: Storage, clock: FakeClock) -> AuthService:
    return AuthService(storage.auth, clock)


@pytest.fixture
async def ready(auth: AuthService) -> AuthService:
    await auth.setup(PASSWORD, "test")
    return auth


async def test_setup_is_required_until_an_admin_exists(auth: AuthService) -> None:
    assert await auth.setup_required() is True
    await auth.setup(PASSWORD, "test")
    assert await auth.setup_required() is False


async def test_setup_works_once_and_logs_the_admin_in(auth: AuthService) -> None:
    issued = await auth.setup(PASSWORD, "Firefox")
    principal = await auth.authenticate_session(issued.token)
    assert principal is not None and principal.kind == "admin" and principal.is_full_admin
    with pytest.raises(AlreadySetUp):
        await auth.setup("another long password", "test")


@pytest.mark.parametrize("password", ["", "short", "123456789"])
async def test_a_short_password_is_refused(auth: AuthService, password: str) -> None:
    with pytest.raises(WeakSecret):
        await auth.setup(password, "test")
    assert await auth.setup_required() is True


async def test_the_password_is_not_stored_in_clear(ready: AuthService, storage: Storage) -> None:
    admin = await storage.auth.get_admin()
    assert admin is not None and PASSWORD not in admin.password_hash


async def test_login_needs_a_set_up_admin(auth: AuthService) -> None:
    with pytest.raises(SetupRequired):
        await auth.login(PASSWORD, "1.2.3.4", "test")


async def test_login_with_the_right_password(ready: AuthService) -> None:
    issued = await ready.login(PASSWORD, "1.2.3.4", "Firefox")
    assert issued.record.kind == "admin" and issued.record.user_agent == "Firefox"
    principal = await ready.authenticate_session(issued.token)
    assert principal is not None
    assert principal.scopes == {"read", "control", "admin"}
    assert principal.session_id == issued.record.id


async def test_login_with_the_wrong_password(ready: AuthService) -> None:
    with pytest.raises(InvalidCredentials):
        await ready.login("wrong password!", "1.2.3.4", "test")


async def test_repeated_failures_lock_the_client_out_for_a_while(
    ready: AuthService, clock: FakeClock
) -> None:
    for _ in range(4):  # three failures are free
        with pytest.raises(InvalidCredentials):
            await ready.login("wrong password!", "1.2.3.4", "test")
    with pytest.raises(RateLimited) as locked:
        await ready.login(PASSWORD, "1.2.3.4", "test")  # even the right one waits
    assert locked.value.retry_after > 0
    await ready.login(PASSWORD, "5.6.7.8", "test")  # another client is unaffected
    clock.advance(seconds=locked.value.retry_after + 1)
    await ready.login(PASSWORD, "1.2.3.4", "test")


async def test_an_unknown_or_forged_session_token_is_not_authenticated(
    ready: AuthService,
) -> None:
    assert await ready.authenticate_session("nope") is None
    assert await ready.authenticate_session("") is None


async def test_only_the_hash_of_the_session_token_is_stored(
    ready: AuthService, storage: Storage
) -> None:
    issued = await ready.login(PASSWORD, "ip", "test")
    assert await storage.auth.get_session(issued.token) is None
    assert await storage.auth.get_session(hash_token(issued.token)) is not None


async def test_an_expired_session_is_refused(ready: AuthService, clock: FakeClock) -> None:
    issued = await ready.login(PASSWORD, "ip", "test")
    clock.advance(days=31)
    assert await ready.authenticate_session(issued.token) is None


async def test_an_admin_session_slides_while_it_is_used(
    ready: AuthService, clock: FakeClock
) -> None:
    issued = await ready.login(PASSWORD, "ip", "test")
    for _ in range(4):
        clock.advance(days=20)
        assert await ready.authenticate_session(issued.token) is not None
    clock.advance(days=31)
    assert await ready.authenticate_session(issued.token) is None


async def test_logout_ends_the_session(ready: AuthService) -> None:
    issued = await ready.login(PASSWORD, "ip", "test")
    assert await ready.revoke_session(issued.record.id) is True
    assert await ready.authenticate_session(issued.token) is None


async def test_the_pin_must_be_four_to_eight_digits(ready: AuthService) -> None:
    for bad in ["", "123", "123456789", "12a4", "١٢٣٤"]:
        with pytest.raises(WeakSecret):
            await ready.set_pin(bad)


async def test_pin_login_gives_a_short_limited_session(
    ready: AuthService, clock: FakeClock
) -> None:
    await ready.set_pin(PIN)
    issued = await ready.login_pin(PIN, "ip", "phone")
    principal = await ready.authenticate_session(issued.token)
    assert principal is not None and principal.kind == "pin"
    assert principal.scopes == {"read", "control"}
    assert not principal.is_full_admin
    clock.advance(hours=11)
    assert await ready.authenticate_session(issued.token) is not None
    assert await ready.authenticate_session(issued.token) is not None  # no sliding
    clock.advance(hours=2)
    assert await ready.authenticate_session(issued.token) is None


async def test_pin_login_without_a_pin_or_with_a_wrong_one(ready: AuthService) -> None:
    with pytest.raises(InvalidCredentials):
        await ready.login_pin(PIN, "ip", "test")
    await ready.set_pin(PIN)
    with pytest.raises(InvalidCredentials):
        await ready.login_pin("0000", "ip", "test")


async def test_five_wrong_pins_lock_it_until_the_next_password_login(
    ready: AuthService, clock: FakeClock
) -> None:
    await ready.set_pin(PIN)
    for i in range(5):
        with pytest.raises(InvalidCredentials):
            await ready.login_pin("0000", f"ip{i}", "test")
    with pytest.raises(PinLocked):
        await ready.login_pin(PIN, "fresh-ip", "test")
    clock.advance(days=1)
    with pytest.raises(PinLocked):
        await ready.login_pin(PIN, "fresh-ip", "test")
    await ready.login(PASSWORD, "ip", "test")
    await ready.login_pin(PIN, "fresh-ip", "test")


async def test_a_right_pin_clears_the_failure_count(ready: AuthService) -> None:
    await ready.set_pin(PIN)
    for i in range(4):
        with pytest.raises(InvalidCredentials):
            await ready.login_pin("0000", f"ip{i}", "test")
    await ready.login_pin(PIN, "ip", "test")
    for i in range(4):
        with pytest.raises(InvalidCredentials):
            await ready.login_pin("0000", f"other{i}", "test")
    await ready.login_pin(PIN, "ip", "test")  # four more failures did not lock it


async def test_removing_the_pin_ends_pin_logins(ready: AuthService) -> None:
    await ready.set_pin(PIN)
    await ready.clear_pin()
    with pytest.raises(InvalidCredentials):
        await ready.login_pin(PIN, "ip", "test")


async def test_changing_the_password_needs_the_current_one_and_ends_other_sessions(
    ready: AuthService,
) -> None:
    keep = await ready.login(PASSWORD, "ip", "this browser")
    other = await ready.login(PASSWORD, "ip", "another")
    with pytest.raises(InvalidCredentials):
        await ready.change_password(
            "not the password", "a brand new password", keep.record.id, "ip"
        )
    with pytest.raises(WeakSecret):
        await ready.change_password(PASSWORD, "short", keep.record.id, "ip")

    await ready.change_password(PASSWORD, "a brand new password", keep.record.id, "ip")
    assert await ready.authenticate_session(keep.token) is not None
    assert await ready.authenticate_session(other.token) is None
    with pytest.raises(InvalidCredentials):
        await ready.login(PASSWORD, "ip2", "test")
    await ready.login("a brand new password", "ip2", "test")


async def test_revoking_the_other_sessions_keeps_the_current_one(ready: AuthService) -> None:
    keep = await ready.login(PASSWORD, "ip", "a")
    other = await ready.login(PASSWORD, "ip", "b")
    # the setup session and the other login go, the kept one stays
    assert await ready.revoke_other_sessions(keep.record.id) == 2
    assert await ready.authenticate_session(keep.token) is not None
    assert await ready.authenticate_session(other.token) is None


async def test_an_api_token_is_shown_once_and_authenticates(
    ready: AuthService, storage: Storage
) -> None:
    issued = await ready.create_token("Home Assistant", {"read", "control"})
    assert issued.token.startswith("tvb_") and len(issued.token) > 40
    assert await storage.auth.get_token(issued.token) is None  # only the hash is stored
    principal = await ready.authenticate_token(issued.token)
    assert principal is not None and principal.kind == "token"
    assert principal.scopes == {"read", "control"}
    assert not principal.is_full_admin
    assert principal.token_id == issued.record.id


async def test_using_a_token_records_when(ready: AuthService, clock: FakeClock) -> None:
    issued = await ready.create_token("HA", {"read"})
    clock.advance(hours=2)
    await ready.authenticate_token(issued.token)
    [record] = await ready.list_tokens()
    assert record.last_used_at == clock.now()


async def test_token_requests_validate_name_and_scopes(ready: AuthService) -> None:
    for name, scopes in [("", {"read"}), ("HA", set()), ("HA", {"root"})]:
        with pytest.raises(WeakSecret):
            await ready.create_token(name, scopes)


async def test_a_revoked_or_unknown_token_is_refused(ready: AuthService) -> None:
    issued = await ready.create_token("HA", {"read"})
    assert await ready.revoke_token(issued.record.id) is True
    assert await ready.authenticate_token(issued.token) is None
    assert await ready.authenticate_token("tvb_unknown") is None
    assert await ready.revoke_token("nope") is False


async def test_expired_sessions_are_purged_on_login(
    ready: AuthService, clock: FakeClock, storage: Storage
) -> None:
    await ready.login(PASSWORD, "ip", "old")
    clock.advance(days=40)
    await ready.login(PASSWORD, "ip", "new")
    assert [s.user_agent for s in await storage.auth.list_sessions()] == ["new"]
