"""Keep the Engine's HTTPS certificate in order: the local CA and the server certificate.

Modes: `auto` (a local CA issues the certificate), `custom` (the user's certificate and key files)
and `off`. The CA lives in the sealed secret settings; uvicorn reads the server certificate from
files under the data folder.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography import x509

from tvbalance.config import EngineConfig
from tvbalance.infra import tls
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import SecretSettingsStore

log = logging.getLogger(__name__)

CA_CERT_SECRET = "tls_ca_cert"
CA_KEY_SECRET = "tls_ca_key"
CHECK_INTERVAL = 6 * 3600.0
REQUEST_TIMEOUT = 10.0

NameSource = Callable[[], Awaitable[list[str]]]


@dataclass(frozen=True, slots=True)
class TlsStatus:
    mode: str
    active: bool
    https_port: int
    names: list[str]
    skipped_names: list[str]
    expires_at: datetime | None
    ca_fingerprint: str | None
    error: str | None


def _primary_ipv4() -> str | None:
    """The address used to reach the local network; a UDP connect sends nothing."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return str(probe.getsockname()[0])
    except OSError:
        return None
    finally:
        probe.close()


def _supervisor_data(config: EngineConfig, path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        config.supervisor_url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {config.supervisor_token}"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = json.load(response)
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else {}


def _supervisor_names(config: EngineConfig) -> list[str]:
    names: list[str] = []
    try:
        hostname = _supervisor_data(config, "/host/info").get("hostname")
        if isinstance(hostname, str) and hostname:
            names += [hostname, hostname + ".local"]
        for interface in _supervisor_data(config, "/network/info").get("interfaces") or []:
            for address in (interface.get("ipv4") or {}).get("address") or []:
                names.append(str(address).split("/")[0])
    except (urllib.error.URLError, OSError, ValueError, AttributeError) as ex:
        log.warning("cannot ask the Supervisor for the host names (%s)", ex)
    return names


def detect_names(config: EngineConfig) -> NameSource:
    async def source() -> list[str]:
        names = ["localhost", "127.0.0.1", "::1", *config.tls_names]
        host = socket.gethostname().lower()
        if host:
            names.append(host if "." in host else host + ".local")
        if (primary := await asyncio.to_thread(_primary_ipv4)) is not None:
            names.append(primary)
        if config.supervisor_token:
            names += await asyncio.to_thread(_supervisor_names, config)
        return names

    return source


def _write_atomic(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(temp, path)


class TlsManager:
    def __init__(
        self,
        secrets: SecretSettingsStore,
        config: EngineConfig,
        clock: Clock,
        names: NameSource | None = None,
        *,
        check_interval: float = CHECK_INTERVAL,
    ) -> None:
        self._secrets, self._config, self._clock = secrets, config, clock
        self._names = names or detect_names(config)
        self._interval = check_interval
        self._dir = config.data_dir / "tls"
        self._ca: tls.LocalCa | None = None
        self._cert_names: list[str] = []
        self._skipped: list[str] = []
        self._expires_at: datetime | None = None
        self._error: str | None = None
        self._ready = False
        self._custom_stamp: tuple[float, float] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task[None] | None = None

    @property
    def mode(self) -> str:
        return self._config.tls_mode

    @property
    def active(self) -> bool:
        return self._ready and self._error is None and self.mode != "off"

    @property
    def certfile(self) -> Path | None:
        if self.mode == "custom":
            return self._config.tls_certfile
        return self._dir / "server.crt" if self.mode == "auto" else None

    @property
    def keyfile(self) -> Path | None:
        if self.mode == "custom":
            return self._config.tls_keyfile
        return self._dir / "server.key" if self.mode == "auto" else None

    def on_renew(self, listener: Callable[[], None]) -> None:
        """Called after the certificate files changed, so a listening server can reload them."""
        self._listeners.append(listener)

    async def prepare(self) -> None:
        """Make the certificate ready. A problem is recorded, not raised: HTTP keeps working."""
        try:
            if self.mode == "auto":
                await self._prepare_auto()
            elif self.mode == "custom":
                self._check_custom()
        except (tls.TlsError, OSError) as ex:
            self._error = str(ex)
            log.error("HTTPS is unavailable: %s", ex)
            return
        self._ready = self.mode != "off"

    async def _load_ca(self) -> tls.LocalCa:
        if self._ca is not None:
            return self._ca
        cert_pem = await self._secrets.get(CA_CERT_SECRET)
        key_pem = await self._secrets.get(CA_KEY_SECRET)
        if cert_pem and key_pem:
            try:
                self._ca = tls.load_ca(cert_pem.encode(), key_pem.encode())
                return self._ca
            except tls.TlsError:
                log.warning("the stored local CA is unusable; creating a new one")
        return await self._new_ca()

    async def _new_ca(self) -> tls.LocalCa:
        ca = tls.create_ca(self._clock.now())
        await self._secrets.set(CA_CERT_SECRET, tls.ca_cert_pem(ca).decode())
        await self._secrets.set(CA_KEY_SECRET, tls.ca_key_pem(ca).decode())
        self._ca = ca
        return ca

    def _existing_server_cert(self, ca: tls.LocalCa) -> x509.Certificate | None:
        assert self.certfile is not None
        try:
            cert = x509.load_pem_x509_certificate(self.certfile.read_bytes())
        except (OSError, ValueError):
            return None
        return cert if cert.issuer == ca.cert.subject else None

    async def _prepare_auto(self, *, force: bool = False) -> bool:
        """Issue the server certificate when missing, near expiry, for other names or forced."""
        ca = await self._load_ca()
        wanted, self._skipped = tls.filter_names(await self._names())
        if self._skipped:
            log.info("not certified (outside the local CA's reach): %s", ", ".join(self._skipped))
        current = self._existing_server_cert(ca)
        if (
            not force
            and current is not None
            and not tls.needs_renewal(current, wanted, self._clock.now())
        ):
            self._cert_names = tls.cert_names(current)
            self._expires_at = current.not_valid_after_utc
            return False
        cert, key = tls.issue_server_cert(ca, wanted, self._clock.now())
        assert self.certfile is not None and self.keyfile is not None
        _write_atomic(self.keyfile, tls.key_pem(key), 0o600)
        _write_atomic(self.certfile, tls.cert_pem(cert), 0o644)
        self._cert_names = tls.cert_names(cert)
        self._expires_at = cert.not_valid_after_utc
        log.info("issued the HTTPS certificate for %s", ", ".join(self._cert_names))
        return True

    def _check_custom(self) -> bool:
        assert self._config.tls_certfile and self._config.tls_keyfile
        info = tls.load_custom(
            self._config.tls_certfile, self._config.tls_keyfile, self._clock.now()
        )
        stamp = (
            self._config.tls_certfile.stat().st_mtime,
            self._config.tls_keyfile.stat().st_mtime,
        )
        changed = self._custom_stamp is not None and stamp != self._custom_stamp
        self._custom_stamp = stamp
        self._cert_names, self._expires_at = info.names, info.expires_at
        return changed

    async def renew_if_needed(self) -> bool:
        """Re-check the certificate; True when the files changed. A failure keeps the old one."""
        if self.mode == "off" or not self._ready:
            return False
        try:
            changed = await self._prepare_auto() if self.mode == "auto" else self._check_custom()
        except (tls.TlsError, OSError) as ex:
            log.error("cannot renew the HTTPS certificate: %s", ex)
            self._error = str(ex)
            return False
        self._error = None
        if changed:
            self._notify()
        return changed

    async def rotate(self) -> None:
        """Replace the CA (and the server certificate). Devices must install the new CA."""
        if self.mode != "auto":
            raise tls.TlsError("The local CA is only used in automatic mode")
        await self._new_ca()
        await self._prepare_auto(force=True)
        self._error = None
        self._ready = True
        self._notify()

    def _notify(self) -> None:
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                log.exception("a certificate listener failed")

    def ca_certificate(self) -> x509.Certificate | None:
        return self._ca.cert if self.mode == "auto" and self._ca is not None else None

    def status(self) -> TlsStatus:
        ca = self.ca_certificate()
        return TlsStatus(
            mode=self.mode,
            active=self.active,
            https_port=self._config.https_port,
            names=list(self._cert_names),
            skipped_names=list(self._skipped),
            expires_at=self._expires_at,
            ca_fingerprint=tls.fingerprint(ca) if ca is not None else None,
            error=self._error,
        )

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self.renew_if_needed()

    def start(self) -> None:
        if self._task is None and self.mode != "off":
            self._task = asyncio.create_task(self.run(), name="tls-renewal")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
