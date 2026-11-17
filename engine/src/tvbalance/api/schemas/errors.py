"""The error envelope every API failure uses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


type Responses = dict[int | str, dict[str, Any]]

AUTH_ERRORS: Responses = {401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}}
NOT_FOUND_ERRORS: Responses = {**AUTH_ERRORS, 404: {"model": ErrorResponse}}
