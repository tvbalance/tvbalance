"""Sign-in, sessions, PIN and API tokens (ADR 0005)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from tvbalance.api.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    Caller,
    FullAdmin,
    get_auth,
)
from tvbalance.api.errors import not_found
from tvbalance.api.schemas.auth import (
    AuthState,
    LoginRequest,
    Me,
    PasswordChange,
    PinLoginRequest,
    PinSet,
    Revoked,
    SessionOut,
    SetupRequest,
    TokenCreate,
    TokenCreated,
    TokenOut,
)
from tvbalance.api.schemas.errors import ErrorResponse
from tvbalance.app.auth import (
    SCOPES,
    AuthService,
    IssuedSession,
    Principal,
    csrf_token_for,
)
from tvbalance.ports.storage import ApiTokenRecord, SessionRecord

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)

Auth = Annotated[AuthService, Depends(get_auth)]


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _agent(request: Request) -> str:
    return request.headers.get("user-agent", "")[:200]


def _set_cookies(response: Response, request: Request, issued: IssuedSession) -> None:
    """The session cookie is HttpOnly; its CSRF companion is readable so the UI can echo it."""
    max_age = int((issued.record.expires_at - issued.record.created_at).total_seconds())
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    for name, value, http_only in (
        (SESSION_COOKIE, issued.token, True),
        (CSRF_COOKIE, csrf_token_for(issued.token), False),
    ):
        response.set_cookie(
            name, value, max_age=max_age, httponly=http_only, samesite="strict", secure=secure
        )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, samesite="strict")


def _me(principal: Principal, session_token: str | None) -> Me:
    return Me(
        kind=principal.kind,
        name=principal.name,
        scopes=sorted(principal.scopes),  # type: ignore[arg-type]
        full_admin=principal.is_full_admin,
        session_id=principal.session_id,
        csrf_token=csrf_token_for(session_token) if session_token else None,
    )


def _signed_in(issued: IssuedSession) -> Me:
    if issued.record.kind == "admin":
        principal = Principal(kind="admin", scopes=SCOPES, session_id=issued.record.id)
    else:
        principal = Principal(
            kind="pin", scopes=frozenset({"read", "control"}), session_id=issued.record.id
        )
    return _me(principal, issued.token)


def _session_out(record: SessionRecord, current_id: str | None) -> SessionOut:
    return SessionOut(
        id=record.id,
        kind="admin" if record.kind == "admin" else "pin",
        created_at=record.created_at,
        last_seen_at=record.last_seen_at,
        expires_at=record.expires_at,
        user_agent=record.user_agent,
        current=record.id == current_id,
    )


def _token_out(record: ApiTokenRecord) -> TokenOut:
    return TokenOut(
        id=record.id,
        name=record.name,
        scopes=sorted(record.scopes),  # type: ignore[arg-type]
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )


@router.get("/state", response_model=AuthState)
async def state(auth: Auth) -> AuthState:
    """Public: tells the UI whether to show the first-run setup or the sign-in form."""
    return AuthState(setup_required=await auth.setup_required())


@router.post("/setup", response_model=Me, status_code=201)
async def setup(body: SetupRequest, request: Request, response: Response, auth: Auth) -> Me:
    """Create the admin account (once) and sign it in."""
    issued = await auth.setup(body.password, _agent(request))
    _set_cookies(response, request, issued)
    return _signed_in(issued)


@router.post("/login", response_model=Me)
async def login(body: LoginRequest, request: Request, response: Response, auth: Auth) -> Me:
    issued = await auth.login(body.password, _client(request), _agent(request))
    _set_cookies(response, request, issued)
    return _signed_in(issued)


@router.post("/pin-login", response_model=Me)
async def pin_login(body: PinLoginRequest, request: Request, response: Response, auth: Auth) -> Me:
    """Quick unlock: a 12-hour session that cannot manage access."""
    issued = await auth.login_pin(body.pin, _client(request), _agent(request))
    _set_cookies(response, request, issued)
    return _signed_in(issued)


@router.post("/logout", status_code=204)
async def logout(principal: Caller, auth: Auth) -> Response:
    if principal.session_id is not None:
        await auth.revoke_session(principal.session_id)
    response = Response(status_code=204)
    _clear_cookies(response)
    return response


@router.get("/me", response_model=Me)
async def me(principal: Caller, request: Request) -> Me:
    token = request.cookies.get(SESSION_COOKIE) if principal.session_id else None
    return _me(principal, token)


@router.put("/password", status_code=204)
async def change_password(
    body: PasswordChange, principal: FullAdmin, request: Request, auth: Auth
) -> Response:
    """Needs the current password; every other session ends."""
    await auth.change_password(
        body.current_password, body.new_password, principal.session_id, _client(request)
    )
    return Response(status_code=204)


@router.put("/pin", status_code=204)
async def set_pin(body: PinSet, _: FullAdmin, auth: Auth) -> Response:
    await auth.set_pin(body.pin)
    return Response(status_code=204)


@router.delete("/pin", status_code=204)
async def clear_pin(_: FullAdmin, auth: Auth) -> Response:
    await auth.clear_pin()
    return Response(status_code=204)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(principal: FullAdmin, auth: Auth) -> list[SessionOut]:
    return [_session_out(s, principal.session_id) for s in await auth.list_sessions()]


@router.delete("/sessions", response_model=Revoked)
async def revoke_other_sessions(principal: FullAdmin, auth: Auth) -> Revoked:
    """Sign out everywhere else."""
    return Revoked(revoked=await auth.revoke_other_sessions(principal.session_id))


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(session_id: str, _: FullAdmin, auth: Auth) -> Response:
    if not await auth.revoke_session(session_id):
        raise not_found("session")
    return Response(status_code=204)


@router.get("/tokens", response_model=list[TokenOut])
async def list_tokens(_: FullAdmin, auth: Auth) -> list[TokenOut]:
    return [_token_out(t) for t in await auth.list_tokens()]


@router.post("/tokens", response_model=TokenCreated, status_code=201)
async def create_token(body: TokenCreate, _: FullAdmin, auth: Auth) -> TokenCreated:
    """The token is in this response only; the engine keeps just its hash."""
    issued = await auth.create_token(body.name, body.scopes)
    return TokenCreated(**_token_out(issued.record).model_dump(), token=issued.token)


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_token(token_id: str, _: FullAdmin, auth: Auth) -> Response:
    if not await auth.revoke_token(token_id):
        raise not_found("token")
    return Response(status_code=204)
