"""The async SQLite engine. Every connection gets the same pragmas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

BUSY_TIMEOUT_MS = 5000


def create_engine(path: Path) -> AsyncEngine:
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")

    @event.listens_for(engine.sync_engine, "connect")
    def _apply_pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        finally:
            cursor.close()

    return engine
