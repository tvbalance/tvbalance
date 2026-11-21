"""Local certificates: a constrained CA, server certificates, renewal and the iOS profile.

The CA can only vouch for private names and addresses (X.509 Name Constraints), so installing it
on a device does not let it vouch for the public internet.
"""

from __future__ import annotations

import ipaddress
import plistlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_COMMON_NAME = "TVBalance Local CA"
CA_LIFETIME = timedelta(days=3650)
SERVER_LIFETIME = timedelta(days=397)  # the longest lifetime Apple platforms accept
RENEW_BEFORE = timedelta(days=30)
BACKDATE = timedelta(hours=1)  # tolerates clocks that run a little behind

PERMITTED_DNS = ("local", "lan", "home.arpa", "internal", "localhost")
PERMITTED_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        (0xC0A80000, 16),  # the private /16 block
        "127.0.0.0/8",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)

_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class TlsError(ValueError):
    """A certificate or key cannot be used."""


@dataclass(frozen=True, slots=True)
class LocalCa:
    cert: x509.Certificate
    key: ec.EllipticCurvePrivateKey


@dataclass(frozen=True, slots=True)
class CertInfo:
    names: list[str]
    expires_at: datetime


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(microsecond=0)


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def create_ca(now: datetime) -> LocalCa:
    now = _utc(now)
    key = ec.generate_private_key(ec.SECP256R1())
    subject = _name(CA_COMMON_NAME)
    permitted: list[x509.GeneralName] = [x509.DNSName(name) for name in PERMITTED_DNS]
    permitted += [x509.IPAddress(net) for net in PERMITTED_NETWORKS]
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - BACKDATE)
        .not_valid_after(now + CA_LIFETIME)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.NameConstraints(permitted, None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return LocalCa(cert, key)


def _parse_ip(name: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(name)
    except ValueError:
        return None


def _dns_allowed(name: str) -> bool:
    labels = name.split(".")
    if not all(_LABEL.match(label) for label in labels):
        return False
    return any(name == suffix or name.endswith("." + suffix) for suffix in PERMITTED_DNS)


def filter_names(names: list[str]) -> tuple[list[str], list[str]]:
    """Split names into those the CA may certify and those it may not (duplicates dropped)."""
    allowed: list[str] = []
    skipped: list[str] = []
    for raw in names:
        name = raw.strip().lower()
        if not name or name in allowed or name in skipped:
            continue
        ip = _parse_ip(name)
        ok = (
            any(ip in net for net in PERMITTED_NETWORKS if net.version == ip.version)
            if ip is not None
            else _dns_allowed(name)
        )
        (allowed if ok else skipped).append(name)
    return allowed, skipped


def issue_server_cert(
    ca: LocalCa, names: list[str], now: datetime
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    allowed, _ = filter_names(names)
    if not allowed:
        raise TlsError("No usable name or address for the server certificate")
    now = _utc(now)
    key = ec.generate_private_key(ec.SECP256R1())
    sans: list[x509.GeneralName] = []
    for name in allowed:
        ip = _parse_ip(name)
        sans.append(x509.IPAddress(ip) if ip is not None else x509.DNSName(name))
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name(allowed[0]))
        .issuer_name(ca.cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - BACKDATE)
        .not_valid_after(now + SERVER_LIFETIME)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.key.public_key()), critical=False
        )
        .sign(ca.key, hashes.SHA256())
    )
    return cert, key


def cert_names(cert: x509.Certificate) -> list[str]:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return []
    return [
        *san.get_values_for_type(x509.DNSName),
        *map(str, san.get_values_for_type(x509.IPAddress)),
    ]


def needs_renewal(cert: x509.Certificate, names: list[str], now: datetime) -> bool:
    if cert.not_valid_after_utc - _utc(now) < RENEW_BEFORE:
        return True
    wanted, _ = filter_names(names)
    return set(wanted) != {name.lower() for name in cert_names(cert)}


def fingerprint(cert: x509.Certificate) -> str:
    digest = cert.fingerprint(hashes.SHA256()).hex().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def cert_pem(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def key_pem(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def ca_cert_pem(ca: LocalCa) -> bytes:
    return cert_pem(ca.cert)


def ca_key_pem(ca: LocalCa) -> bytes:
    return key_pem(ca.key)


def load_ca(cert_data: bytes, key_data: bytes) -> LocalCa:
    try:
        cert = x509.load_pem_x509_certificate(cert_data)
        key = serialization.load_pem_private_key(key_data, password=None)
    except ValueError as ex:
        raise TlsError(f"Cannot read the CA: {ex}") from ex
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise TlsError("The CA key must be an EC key")
    return LocalCa(cert, key)


def mobileconfig(cert: x509.Certificate) -> bytes:
    """An unsigned iOS/macOS profile that installs the CA."""
    seed = fingerprint(cert)
    profile = {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": "dev.tvbalance.local-ca",
        "PayloadUUID": str(uuid.uuid5(uuid.NAMESPACE_DNS, "profile." + seed)),
        "PayloadDisplayName": CA_COMMON_NAME,
        "PayloadContent": [
            {
                "PayloadType": "com.apple.security.root",
                "PayloadVersion": 1,
                "PayloadIdentifier": "dev.tvbalance.local-ca.root",
                "PayloadUUID": str(uuid.uuid5(uuid.NAMESPACE_DNS, "root." + seed)),
                "PayloadDisplayName": CA_COMMON_NAME,
                "PayloadContent": cert.public_bytes(serialization.Encoding.DER),
            }
        ],
    }
    return plistlib.dumps(profile)


def load_custom(certfile: Path, keyfile: Path, now: datetime) -> CertInfo:
    """Check a certificate and key supplied by the user."""
    try:
        cert = x509.load_pem_x509_certificate(certfile.read_bytes())
    except (OSError, ValueError) as ex:
        raise TlsError(f"Cannot read the certificate {certfile.name}: {ex}") from ex
    try:
        key = serialization.load_pem_private_key(keyfile.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as ex:
        raise TlsError(f"Cannot read the private key {keyfile.name}: {ex}") from ex
    public = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    if key.public_key().public_bytes(*public) != cert.public_key().public_bytes(*public):
        raise TlsError("The private key does not match the certificate")
    if cert.not_valid_after_utc <= _utc(now):
        raise TlsError("The certificate has expired")
    return CertInfo(cert_names(cert), cert.not_valid_after_utc)
