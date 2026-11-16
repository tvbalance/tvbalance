"""One error envelope for the whole API: ``{"error": {"code", "message", "details"?}}``."""

from __future__ import annotations

import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tvbalance.app.auth import (
    AlreadySetUp,
    AuthError,
    InvalidCredentials,
    PinLocked,
    RateLimited,
    SetupRequired,
    WeakSecret,
)

_AUTH_STATUS: dict[type[AuthError], int] = {
    SetupRequired: 409,
    AlreadySetUp: 409,
    InvalidCredentials: 401,
    PinLocked: 403,
    WeakSecret: 422,
    RateLimited: 429,
}
_HTTP_CODES = {
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_failed",
    429: "rate_limited",
    503: "unavailable",
}


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers


def not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", f"{what} not found")


def _response(
    status: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _response(exc.status, exc.code, exc.message, exc.headers)

    @app.exception_handler(AuthError)
    async def auth_error(_: Request, exc: AuthError) -> JSONResponse:
        status = _AUTH_STATUS.get(type(exc), 401)
        headers = None
        if isinstance(exc, RateLimited):
            headers = {"Retry-After": str(max(1, math.ceil(exc.retry_after)))}
        return _response(status, exc.code, str(exc), headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e["loc"]), "message": e["msg"], "type": e["type"]}
            for e in jsonable_encoder(exc.errors(), exclude={"input", "ctx", "url"})
        ]
        return _response(422, "validation_failed", "the request is not valid", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return _response(exc.status_code, code, str(exc.detail), dict(exc.headers or {}))
