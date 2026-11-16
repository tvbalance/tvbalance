"""Fixtures shared by the engine tests. Importing this directory also puts `support` on the path."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig


@pytest.fixture(autouse=True)
def cheap_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Argon2 at production cost takes ~100 ms per hash; tests only need the same behavior."""
    from argon2 import PasswordHasher

    from tvbalance.infra import passwords

    monkeypatch.setattr(
        passwords, "_hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    )


@pytest.fixture
def engine_config(tmp_path: Path) -> EngineConfig:
    return EngineConfig(data_dir=tmp_path / "data")


@pytest.fixture
def app_client(engine_config: EngineConfig) -> Iterator[TestClient]:
    """A running app (lifespan included) with an empty storage and no adapters."""
    app = create_app(plugins={}, config=engine_config)
    with TestClient(app) as client:
        yield client
