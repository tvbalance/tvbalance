"""Engine configuration, read once from the environment."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_DATA_DIR = Path("data")
DEFAULT_SUPERVISOR_URL = "http://supervisor"
DEFAULT_HTTPS_PORT = 8766
# Home Assistant mounts certificates here; Add-on options name them relative to this folder.
ADDON_SSL_DIR = Path("/ssl")
TLS_MODES = ("auto", "off")


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
    # Set only inside a Home Assistant Add-on, where the Supervisor can announce the Engine.
    supervisor_token: str | None = field(default=None, repr=False)
    supervisor_url: str = DEFAULT_SUPERVISOR_URL
    # "auto": a local CA issues the certificate; "custom": the user's files; "off": HTTP only.
    tls_mode: str = "auto"
    https_port: int = DEFAULT_HTTPS_PORT
    tls_certfile: Path | None = None
    tls_keyfile: Path | None = None
    tls_names: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> EngineConfig:
        data_dir = _path(environ.get("TVBALANCE_DATA_DIR")) or DEFAULT_DATA_DIR
        options = _addon_options(data_dir)
        port = _port(environ.get("TVBALANCE_PORT"))
        https_port = _port(
            environ.get("TVBALANCE_HTTPS_PORT"), "TVBALANCE_HTTPS_PORT", DEFAULT_HTTPS_PORT
        )
        if https_port == port:
            raise ConfigError("HTTP and HTTPS need different ports")
        certfile = _path(environ.get("TVBALANCE_TLS_CERTFILE")) or _option_path(
            options, "tls_certfile"
        )
        keyfile = _path(environ.get("TVBALANCE_TLS_KEYFILE")) or _option_path(
            options, "tls_keyfile"
        )
        if (certfile is None) != (keyfile is None):
            raise ConfigError(
                "TVBALANCE_TLS_CERTFILE and TVBALANCE_TLS_KEYFILE must be set together"
            )
        mode = environ.get("TVBALANCE_TLS") or str(options.get("tls") or "auto")
        if mode not in TLS_MODES:
            raise ConfigError(f"TVBALANCE_TLS must be one of {', '.join(TLS_MODES)}, got {mode!r}")
        if mode == "auto" and certfile is not None:
            mode = "custom"
        names = environ.get("TVBALANCE_TLS_NAMES")
        listed = names.split(",") if names else _option_list(options, "tls_names")
        return cls(
            host=environ.get("TVBALANCE_HOST") or DEFAULT_HOST,
            port=port,
            web_dir=_path(environ.get("TVBALANCE_WEB_DIR")),
            data_dir=data_dir,
            ingress_trusted=frozenset(
                peer.strip()
                for peer in (environ.get("TVBALANCE_INGRESS_TRUSTED") or "").split(",")
                if peer.strip()
            ),
            supervisor_token=environ.get("SUPERVISOR_TOKEN") or None,
            supervisor_url=environ.get("TVBALANCE_SUPERVISOR_URL") or DEFAULT_SUPERVISOR_URL,
            tls_mode=mode,
            https_port=https_port,
            tls_certfile=certfile,
            tls_keyfile=keyfile,
            tls_names=tuple(name.strip() for name in listed if name.strip()),
        )


def _port(raw: str | None, name: str = "TVBALANCE_PORT", default: int = DEFAULT_PORT) -> int:
    if raw is None:
        return default
    try:
        port = int(raw)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise ConfigError(f"{name} must be a number between 1 and 65535, got {raw!r}")
    return port


def _addon_options(data_dir: Path) -> dict[str, Any]:
    """The options the Supervisor writes for an Add-on; anything unreadable counts as none."""
    try:
        loaded = json.loads((data_dir / "options.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _option_path(options: Mapping[str, Any], key: str) -> Path | None:
    value = options.get(key)
    if not isinstance(value, str) or not value:
        return None
    return ADDON_SSL_DIR / value


def _option_list(options: Mapping[str, Any], key: str) -> list[str]:
    value = options.get(key)
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _path(raw: str | None) -> Path | None:
    return Path(raw) if raw else None
