"""Offline Ed25519 license keys: ``b64url(payload).b64url(signature)``.

Verification is open; only the holder of the private key can issue a license. The gate itself
(what Free and Pro allow) lives in ``app/licensing.py``.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PRODUCT = "tvbalance"
TIER = "pro"
PAYLOAD_VERSION = 1

# Public keys (unpadded base64url) whose licenses this build accepts; more than one allows rotation.
# Empty until the production key pair is generated (see docs/operations/licensing.md): all Free.
TRUSTED_PUBLIC_KEYS: tuple[str, ...] = ()


class LicenseError(Exception):
    """Malformed key, invalid signature or unusable payload."""


@dataclass(frozen=True, slots=True)
class LicensePayload:
    license_id: str
    licensee: str
    issued_at: datetime
    expires_at: datetime | None  # ``None``: perpetual


def _b64_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_keypair() -> tuple[bytes, str]:
    """A new signing key: the private key as PEM and the public key as base64url."""
    private = Ed25519PrivateKey.generate()
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return pem, _b64_encode(public)


def sign_license(payload: object, private_pem: bytes) -> str:
    """Sign ``payload`` (compact JSON, sorted keys) and return the license key."""
    key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("the private key must be an Ed25519 key")
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"{_b64_encode(body)}.{_b64_encode(key.sign(body))}"


def verify_license(key: str, public_keys: Iterable[str]) -> LicensePayload:
    """Check format, signature (against any trusted key) and payload; any problem raises."""
    parts = key.strip().split(".")
    if len(parts) != 2:
        raise LicenseError("malformed license key: expected payload.signature")
    try:
        body = _b64_decode(parts[0])
        signature = _b64_decode(parts[1])
    except ValueError as ex:
        raise LicenseError("malformed license key: not base64url") from ex
    if not any(_signed_by(public, signature, body) for public in public_keys):
        raise LicenseError("the signature does not match a trusted key")
    try:
        raw = json.loads(body)
    except ValueError as ex:
        raise LicenseError("unreadable license payload") from ex
    return _payload(raw)


def _signed_by(public_b64: str, signature: bytes, body: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(_b64_decode(public_b64)).verify(signature, body)
    except (InvalidSignature, ValueError):
        return False
    return True


def _payload(raw: object) -> LicensePayload:
    if not isinstance(raw, dict):
        raise LicenseError("license payload must be an object")
    if raw.get("v") != PAYLOAD_VERSION:
        raise LicenseError("unsupported license version")
    if raw.get("product") != PRODUCT or raw.get("tier") != TIER:
        raise LicenseError("not a TVBalance Pro license")
    license_id, licensee = raw.get("license_id"), raw.get("licensee")
    if not isinstance(license_id, str) or not license_id:
        raise LicenseError("license_id is missing")
    if not isinstance(licensee, str):
        raise LicenseError("licensee must be text")
    issued_at = _date(raw.get("issued_at"), "issued_at")
    expires_raw = raw.get("expires_at")
    expires_at = None if expires_raw is None else _date(expires_raw, "expires_at")
    return LicensePayload(license_id, licensee, issued_at, expires_at)


def _date(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise LicenseError(f"{name} must be a date")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as ex:
        raise LicenseError(f"{name} is not a valid date") from ex
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
