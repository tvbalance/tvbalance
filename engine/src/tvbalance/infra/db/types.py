"""Column types. SQLite drops time zones, so datetimes are stored as UTC and returned aware."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: attach a time zone before storing it")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)
