from __future__ import annotations

import ipaddress
import plistlib
import socket
import ssl
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from tvbalance.infra import tls

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def _san(cert: x509.Certificate) -> x509.SubjectAlternativeName:
    return cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value


def test_ca_is_constrained_to_private_names() -> None:
    ca = tls.create_ca(NOW)
    basic = ca.cert.extensions.get_extension_for_class(x509.BasicConstraints)
    assert basic.critical and basic.value.ca and basic.value.path_length == 0
    constraints = ca.cert.extensions.get_extension_for_class(x509.NameConstraints)
    assert constraints.critical
    permitted = constraints.value.permitted_subtrees or []
    assert x509.DNSName("local") in permitted
    assert not any(isinstance(n, x509.DNSName) and n.value in ("com", "") for n in permitted)
    assert ca.cert.not_valid_after_utc - NOW > timedelta(days=3000)


def test_filter_names_splits_allowed_and_skipped() -> None:
    allowed, skipped = tls.filter_names(
        [
            "localhost",
            "tv.local",
            "10.1.2.3",
            "10.0.0.5",
            "8.8.8.8",
            "example.com",
            "::1",
            "bad name",
        ]
    )
    assert allowed == ["localhost", "tv.local", "10.1.2.3", "10.0.0.5", "::1"]
    assert skipped == ["8.8.8.8", "example.com", "bad name"]


def test_server_certificate_has_san_and_short_life() -> None:
    ca = tls.create_ca(NOW)
    cert, _key = tls.issue_server_cert(ca, ["tvbalance.local", "10.1.2.3"], NOW)
    san = _san(cert)
    assert san.get_values_for_type(x509.DNSName) == ["tvbalance.local"]
    assert [str(ip) for ip in san.get_values_for_type(x509.IPAddress)] == ["10.1.2.3"]
    assert cert.not_valid_after_utc - NOW == timedelta(days=397)
    assert cert.issuer == ca.cert.subject


def test_server_certificate_needs_a_usable_name() -> None:
    ca = tls.create_ca(NOW)
    with pytest.raises(tls.TlsError):
        tls.issue_server_cert(ca, [], NOW)


def test_needs_renewal() -> None:
    ca = tls.create_ca(NOW)
    names = ["localhost", "10.1.2.3"]
    cert, _ = tls.issue_server_cert(ca, names, NOW)
    assert not tls.needs_renewal(cert, names, NOW + timedelta(days=100))
    assert tls.needs_renewal(cert, names, NOW + timedelta(days=370))
    assert tls.needs_renewal(cert, [*names, "10.1.2.4"], NOW)


def test_pem_round_trip_and_fingerprint() -> None:
    ca = tls.create_ca(NOW)
    again = tls.load_ca(tls.ca_cert_pem(ca), tls.ca_key_pem(ca))
    assert again.cert == ca.cert
    fp = tls.fingerprint(ca.cert)
    assert len(fp.split(":")) == 32 and fp == fp.upper()


def test_mobileconfig_carries_the_ca() -> None:
    ca = tls.create_ca(NOW)
    profile = plistlib.loads(tls.mobileconfig(ca.cert))
    payload = profile["PayloadContent"][0]
    assert payload["PayloadType"] == "com.apple.security.root"
    assert payload["PayloadContent"] == ca.cert.public_bytes(serialization.Encoding.DER)


def _serve_once(certfile: Path, keyfile: Path) -> tuple[int, threading.Thread]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile, keyfile)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def run() -> None:
        try:
            conn, _ = listener.accept()
            with context.wrap_socket(conn, server_side=True) as secure:
                secure.recv(1)
        except OSError:
            pass
        finally:
            listener.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return listener.getsockname()[1], thread


def test_real_handshake_trusts_the_local_ca(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    ca = tls.create_ca(now)
    cert, key = tls.issue_server_cert(ca, ["localhost", "127.0.0.1"], now)
    certfile, keyfile = tmp_path / "s.crt", tmp_path / "s.key"
    certfile.write_bytes(tls.cert_pem(cert))
    keyfile.write_bytes(tls.key_pem(key))
    port, thread = _serve_once(certfile, keyfile)
    context = ssl.create_default_context(cadata=tls.cert_pem(ca.cert).decode())
    with socket.create_connection(("127.0.0.1", port)) as raw:
        with context.wrap_socket(raw, server_hostname="127.0.0.1") as secure:
            secure.send(b"x")
    thread.join(5)

    other = tls.create_ca(now)
    port, thread = _serve_once(certfile, keyfile)
    untrusting = ssl.create_default_context(cadata=tls.cert_pem(other.cert).decode())
    with socket.create_connection(("127.0.0.1", port)) as raw:
        with pytest.raises(ssl.SSLCertVerificationError):
            untrusting.wrap_socket(raw, server_hostname="127.0.0.1")
    thread.join(5)


def test_load_custom_validates_the_pair(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    ca = tls.create_ca(now)
    cert, key = tls.issue_server_cert(ca, ["localhost"], now)
    _, other_key = tls.issue_server_cert(ca, ["localhost"], now)
    certfile, keyfile = tmp_path / "c.crt", tmp_path / "c.key"
    certfile.write_bytes(tls.cert_pem(cert))
    keyfile.write_bytes(tls.key_pem(key))
    info = tls.load_custom(certfile, keyfile, now)
    assert info.names == ["localhost"] and info.expires_at == cert.not_valid_after_utc

    keyfile.write_bytes(tls.key_pem(other_key))
    with pytest.raises(tls.TlsError, match="match"):
        tls.load_custom(certfile, keyfile, now)
    keyfile.write_bytes(tls.key_pem(key))
    with pytest.raises(tls.TlsError, match="expired"):
        tls.load_custom(certfile, keyfile, now + timedelta(days=800))
    with pytest.raises(tls.TlsError, match="read"):
        tls.load_custom(tmp_path / "missing.crt", keyfile, now)


def test_filter_names_allows_the_private_sixteen_block() -> None:
    home = str(ipaddress.ip_address(0xC0A80114))
    allowed, skipped = tls.filter_names([home])
    assert allowed == [home] and skipped == []
