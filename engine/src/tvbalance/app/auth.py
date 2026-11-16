"""Authentication and authorization rules, free of any web framework (ADR 0005).

The admin account has a password; a PIN is a quick-unlock convenience on top of it and never the
root of trust. Sessions and API tokens are random secrets of which only the SHA-256 is stored.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from tvbalance.app.ratelimit import RateLimiter
from tvbalance.infra.passwords import hash_secret, verify_secret
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import ApiTokenRecord, AuthStore, SessionRecord

SCOPES = frozenset({"read", "control", "admin"})
TOKEN_PREFIX = "tvb_"
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256
MAX_PIN_FAILURES = 5
ADMIN_SESSION_TTL = timedelta(days=30)
PIN_SESSION_TTL = timedelta(hours=12)
# Sliding sessions and last-use times are refreshed at most this often, to spare the database.
TOUCH_EVERY = timedelta(minutes=5)

PrincipalKind = Literal["admin", "pin", "token", "ingress"]


class AuthError(Exception):
    """Base of the errors the API turns into stable error codes."""

    code = "not_authenticated"


class SetupRequired(AuthError):
    code = "setup_required"


class AlreadySetUp(AuthError):
    code = "conflict"


class InvalidCredentials(AuthError):
    code = "not_authenticated"


class PinLocked(AuthError):
    code = "pin_locked"


class WeakSecret(AuthError):
    """A password, PIN, token name or scope list that is not acceptable."""

    code = "validation_failed"


class RateLimited(AuthError):
    code = "rate_limited"

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"too many attempts, retry in {retry_after:.0f} s")
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is calling. Only an admin session or the Home Assistant user may manage access itself."""

    kind: PrincipalKind
    scopes: frozenset[str]
    name: str = ""
    session_id: str | None = None
    token_id: str | None = None

    @property
    def is_full_admin(self) -> bool:
        return self.kind in ("admin", "ingress")


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str  # shown to the client once; the store keeps its hash
    record: SessionRecord


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    record: ApiTokenRecord


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(session_token: str) -> str:
    """The value a cookie-authenticated write must echo: unguessable without the session token."""
    return hashlib.sha256(b"csrf:" + session_token.encode()).hexdigest()[:32]


class AuthService:
    def __init__(self, store: AuthStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock
        self._password_limiter = RateLimiter(clock, free_attempts=3, base_delay=2.0)
        self._pin_limiter = RateLimiter(clock, free_attempts=2, base_delay=5.0)

    # --- the admin account ---------------------------------------------------------------------

    async def setup_required(self) -> bool:
        return await self._store.get_admin() is None

    async def setup(self, password: str, user_agent: str) -> IssuedSession:
        _check_password(password)
        if not await self._store.create_admin(hash_secret(password)):
            raise AlreadySetUp("the admin account already exists")
        return await self._new_session("admin", user_agent)

    async def login(self, password: str, client: str, user_agent: str) -> IssuedSession:
        await self._verify_password(password, client)
        await self._store.reset_pin_failures()  # a password login unlocks the PIN again
        await self._store.purge_expired_sessions(self._clock.now())
        return await self._new_session("admin", user_agent)

    async def change_password(
        self, current: str, new: str, keep_session_id: str | None, client: str
    ) -> None:
        await self._verify_password(current, client)
        _check_password(new)
        await self._store.set_password_hash(hash_secret(new))
        await self._store.revoke_all_sessions(except_id=keep_session_id)

    async def _verify_password(self, password: str, client: str) -> None:
        admin = await self._store.get_admin()
        if admin is None:
            raise SetupRequired("the admin account is not set up")
        self._raise_if_limited(self._password_limiter, client)
        if not verify_secret(admin.password_hash, password):
            self._password_limiter.failure(client)
            raise InvalidCredentials("wrong password")
        self._password_limiter.success(client)

    # --- the PIN -------------------------------------------------------------------------------

    async def set_pin(self, pin: str) -> None:
        if not re.fullmatch(r"[0-9]{4,8}", pin):
            raise WeakSecret("the PIN must be 4 to 8 digits")
        await self._store.set_pin_hash(hash_secret(pin))

    async def clear_pin(self) -> None:
        await self._store.set_pin_hash(None)

    async def login_pin(self, pin: str, client: str, user_agent: str) -> IssuedSession:
        admin = await self._store.get_admin()
        if admin is None:
            raise SetupRequired("the admin account is not set up")
        if admin.pin_failures >= MAX_PIN_FAILURES:
            raise PinLocked("too many wrong PINs: sign in with the password")
        self._raise_if_limited(self._pin_limiter, client)
        if admin.pin_hash is None or not verify_secret(admin.pin_hash, pin):
            self._pin_limiter.failure(client)
            if admin.pin_hash is not None:
                await self._store.record_pin_failure()
            raise InvalidCredentials("wrong PIN")
        self._pin_limiter.success(client)
        await self._store.reset_pin_failures()
        return await self._new_session("pin", user_agent)

    # --- sessions ------------------------------------------------------------------------------

    async def authenticate_session(self, token: str) -> Principal | None:
        if not token:
            return None
        record = await self._store.get_session(hash_token(token))
        now = self._clock.now()
        if record is None or record.expires_at <= now:
            return None
        if record.kind == "admin" and now - record.last_seen_at >= TOUCH_EVERY:
            await self._store.touch_session(record.id, now, now + ADMIN_SESSION_TTL)
        return Principal(
            kind="admin" if record.kind == "admin" else "pin",
            scopes=SCOPES if record.kind == "admin" else frozenset({"read", "control"}),
            session_id=record.id,
        )

    async def list_sessions(self) -> list[SessionRecord]:
        return await self._store.list_sessions()

    async def revoke_session(self, session_id: str) -> bool:
        return await self._store.revoke_session(session_id)

    async def revoke_other_sessions(self, keep_session_id: str | None) -> int:
        return await self._store.revoke_all_sessions(except_id=keep_session_id)

    async def _new_session(self, kind: Literal["admin", "pin"], user_agent: str) -> IssuedSession:
        ttl = ADMIN_SESSION_TTL if kind == "admin" else PIN_SESSION_TTL
        token = secrets.token_urlsafe(32)
        record = await self._store.add_session(
            hash_token(token), kind, self._clock.now() + ttl, user_agent
        )
        return IssuedSession(token, record)

    # --- API tokens ----------------------------------------------------------------------------

    async def create_token(self, name: str, scopes: Iterable[str]) -> IssuedToken:
        wanted = frozenset(scopes)
        if not name.strip():
            raise WeakSecret("a token needs a name")
        if not wanted or not wanted <= SCOPES:
            raise WeakSecret(f"scopes must be a non-empty subset of {sorted(SCOPES)}")
        token = TOKEN_PREFIX + secrets.token_urlsafe(32)
        record = await self._store.add_token(name.strip(), hash_token(token), wanted)
        return IssuedToken(token, record)

    async def authenticate_token(self, token: str) -> Principal | None:
        if not token.startswith(TOKEN_PREFIX):
            return None
        record = await self._store.get_token(hash_token(token))
        if record is None:
            return None
        now = self._clock.now()
        if record.last_used_at is None or now - record.last_used_at >= TOUCH_EVERY:
            await self._store.touch_token(record.id, now)
        return Principal(kind="token", scopes=record.scopes, name=record.name, token_id=record.id)

    async def list_tokens(self) -> list[ApiTokenRecord]:
        return await self._store.list_tokens()

    async def revoke_token(self, token_id: str) -> bool:
        return await self._store.revoke_token(token_id)

    # --- helpers -------------------------------------------------------------------------------

    @staticmethod
    def _raise_if_limited(limiter: RateLimiter, client: str) -> None:
        wait = limiter.retry_after(client)
        if wait > 0:
            raise RateLimited(wait)


def _check_password(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise WeakSecret(
            f"the password must have {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
        )
