"""Engine configuration, read once from the environment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_DATA_DIR = Path("data")


class ConfigError(ValueError):
    """An environment variable has an unusable value."""


@dataclass(frozen=True, slots=True)
class EngineConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    web_dir: Path | None = None
    data_dir: Path = DEFAULT_DATA_DIR
    # Peers (the Supervisor, under Home Assistant) whose Ingress user headers are believed.
    ingress_trusted: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> EngineConfig:
        return cls(
            host=environ.get("TVBALANCE_HOST") or DEFAULT_HOST,
            port=_port(environ.get("TVBALANCE_PORT")),
            web_dir=_path(environ.get("TVBALANCE_WEB_DIR")),
            data_dir=_path(environ.get("TVBALANCE_DATA_DIR")) or DEFAULT_DATA_DIR,
            ingress_trusted=frozenset(
                peer.strip()
                for peer in (environ.get("TVBALANCE_INGRESS_TRUSTED") or "").split(",")
                if peer.strip()
            ),
        )


def _port(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise ConfigError(f"TVBALANCE_PORT must be a number between 1 and 65535, got {raw!r}")
    return port


def _path(raw: str | None) -> Path | None:
    return Path(raw) if raw else None
