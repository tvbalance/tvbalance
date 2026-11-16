"""Request dependencies: who is calling, and what they may do.

Credentials are tried in this order: Home Assistant Ingress user headers (only from a trusted peer),
an API token (``Authorization: Bearer``), then the session cookie.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from tvbalance.api.errors import ApiError
from tvbalance.app.auth import SCOPES, AuthService, Principal, csrf_token_for
from tvbalance.ports.storage import Storage

SESSION_COOKIE = "tvb_session"
CSRF_COOKIE = "tvb_csrf"
CSRF_HEADER = "X-TVBalance-CSRF"
INGRESS_USER_HEADER = "X-Remote-User-Id"
INGRESS_NAME_HEADER = "X-Remote-User-Name"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

log = logging.getLogger(__name__)


def get_auth(conn: HTTPConnection) -> AuthService:
    auth: AuthService | None = getattr(conn.app.state, "auth", None)
    if auth is None:
        raise ApiError(503, "unavailable", "the engine is not ready")
    return auth


def get_storage(conn: HTTPConnection) -> Storage:
    storage: Storage | None = getattr(conn.app.state, "storage", None)
    if storage is None:
        raise ApiError(503, "unavailable", "the engine is not ready")
    return storage


async def resolve_principal(
    conn: HTTPConnection, auth: AuthService, *, check_csrf: bool
) -> Principal | None:
    """The caller, or None when there is no valid credential.

    A presented but wrong API token is an error rather than a fall-through, so a client that
    holds a stale token never silently acts with some other identity.
    """
    ingress_user = conn.headers.get(INGRESS_USER_HEADER)
    if ingress_user:
        peer = conn.client.host if conn.client else ""
        if peer in conn.app.state.ingress_trusted:
            name = conn.headers.get(INGRESS_NAME_HEADER) or ingress_user
            return Principal(kind="ingress", scopes=SCOPES, name=name)
        log.warning("ignoring Ingress user headers from untrusted peer %s", peer)

    scheme, _, credentials = conn.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and credentials:
        principal = await auth.authenticate_token(credentials.strip())
        if principal is None:
            raise ApiError(401, "not_authenticated", "the API token is not valid")
        return principal

    session_token = conn.cookies.get(SESSION_COOKIE)
    if session_token:
        principal = await auth.authenticate_session(session_token)
        unsafe = conn.scope.get("method", "GET") not in SAFE_METHODS
        if principal is not None and check_csrf and unsafe:
            supplied = conn.headers.get(CSRF_HEADER, "")
            if not hmac.compare_digest(supplied, csrf_token_for(session_token)):
                raise ApiError(403, "forbidden", f"missing or wrong {CSRF_HEADER} header")
        return principal
    return None


async def current_principal(conn: HTTPConnection) -> Principal:
    auth = get_auth(conn)
    principal = await resolve_principal(conn, auth, check_csrf=True)
    if principal is None:
        if await auth.setup_required():
            raise ApiError(401, "setup_required", "create the admin account first")
        raise ApiError(401, "not_authenticated", "sign in or send an API token")
    return principal


Caller = Annotated[Principal, Depends(current_principal)]


async def _full_admin(principal: Caller) -> Principal:
    """Managing access itself (password, PIN, sessions, tokens) needs the admin or the HA user."""
    if not principal.is_full_admin:
        raise ApiError(403, "forbidden", "this needs the admin password or the Home Assistant user")
    return principal


def _require(scope: str) -> Callable[[Caller], Awaitable[Principal]]:
    async def check(principal: Caller) -> Principal:
        if scope not in principal.scopes:
            raise ApiError(403, "forbidden", f"this needs the '{scope}' scope")
        return principal

    return check


# Route parameters: `principal: CanRead` and so on.
CanRead = Annotated[Principal, Depends(_require("read"))]
CanControl = Annotated[Principal, Depends(_require("control"))]
CanAdmin = Annotated[Principal, Depends(_require("admin"))]
FullAdmin = Annotated[Principal, Depends(_full_admin)]
