from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import pytest

from tvbalance.infra.licensing import (
    LicenseError,
    LicensePayload,
    generate_keypair,
    sign_license,
    verify_license,
)

ISSUED = datetime(2026, 1, 1, tzinfo=UTC)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _payload(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "v": 1,
        "product": "tvbalance",
        "tier": "pro",
        "license_id": "abc",
        "licensee": "Rossi",
        "issued_at": ISSUED.isoformat(),
        "expires_at": None,
    }
    return {**base, **changes}


def test_round_trip() -> None:
    private, public = generate_keypair()
    key = sign_license(_payload(), private)
    assert verify_license(key, (public,)) == LicensePayload(
        license_id="abc", licensee="Rossi", issued_at=ISSUED, expires_at=None
    )


def test_expiry_is_parsed() -> None:
    private, public = generate_keypair()
    key = sign_license(_payload(expires_at="2027-01-01T00:00:00+00:00"), private)
    assert verify_license(key, (public,)).expires_at == datetime(2027, 1, 1, tzinfo=UTC)


def test_naive_expiry_is_read_as_utc() -> None:
    private, public = generate_keypair()
    key = sign_license(_payload(expires_at="2027-01-01"), private)
    assert verify_license(key, (public,)).expires_at == datetime(2027, 1, 1, tzinfo=UTC)


def test_tampered_payload_is_rejected() -> None:
    private, public = generate_keypair()
    body, signature = sign_license(_payload(), private).split(".")
    forged = _b64(json.dumps(_payload(licensee="Mallory")).encode()) + "." + signature
    assert body != forged.split(".")[0]
    with pytest.raises(LicenseError):
        verify_license(forged, (public,))


def test_unknown_key_is_rejected() -> None:
    private, _ = generate_keypair()
    _, other_public = generate_keypair()
    with pytest.raises(LicenseError):
        verify_license(sign_license(_payload(), private), (other_public,))


def test_no_trusted_keys_rejects_everything() -> None:
    private, _ = generate_keypair()
    with pytest.raises(LicenseError):
        verify_license(sign_license(_payload(), private), ())


def test_rotation_accepts_either_trusted_key() -> None:
    old_private, old_public = generate_keypair()
    _, new_public = generate_keypair()
    key = sign_license(_payload(), old_private)
    assert verify_license(key, (new_public, old_public)).licensee == "Rossi"


@pytest.mark.parametrize("key", ["", "nodot", "a.b.c", "!!!.???"])
def test_malformed_key(key: str) -> None:
    _, public = generate_keypair()
    with pytest.raises(LicenseError):
        verify_license(key, (public,))


def test_whitespace_around_the_key_is_ignored() -> None:
    private, public = generate_keypair()
    key = sign_license(_payload(), private)
    assert verify_license(f"  {key}\n", (public,)).license_id == "abc"


@pytest.mark.parametrize(
    "changes",
    [
        {"product": "other"},
        {"tier": "free"},
        {"v": 2},
        {"license_id": ""},
        {"licensee": 3},
        {"issued_at": "not a date"},
        {"expires_at": "not a date"},
        {"expires_at": 5},
    ],
)
def test_unusable_payload_is_rejected(changes: dict[str, object]) -> None:
    private, public = generate_keypair()
    with pytest.raises(LicenseError):
        verify_license(sign_license(_payload(**changes), private), (public,))


def test_payload_must_be_an_object() -> None:
    private, public = generate_keypair()
    with pytest.raises(LicenseError):
        verify_license(sign_license([1, 2], private), (public,))  # type: ignore[arg-type]


def test_signed_garbage_is_rejected() -> None:
    private, public = generate_keypair()
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    signer = load_pem_private_key(private, password=None)
    body = b"not json"
    key = _b64(body) + "." + _b64(signer.sign(body))  # type: ignore[union-attr]
    with pytest.raises(LicenseError):
        verify_license(key, (public,))


def test_sign_rejects_a_non_ed25519_key() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with pytest.raises(TypeError):
        sign_license(_payload(), pem)
