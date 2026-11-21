import json
import struct

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from tvbalance.infra.webpush import (
    PushTarget,
    SendResult,
    VapidKeys,
    WebPushSender,
    b64url_decode,
    b64url_encode,
    encrypt,
)

# Browser-side keys of RFC 8291 appendix A.
UA_PRIVATE = "q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94"
UA_PUBLIC = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
)
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
SALT = b64url_decode("DGv6ra1nlYgDCS1FRnbzlw")
AS_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
AS_PUBLIC = (
    "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
)
ENDPOINT = "https://push.example.net/send/abc"


def _private(encoded: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(b64url_decode(encoded), "big"), ec.SECP256R1())


def decrypt(body: bytes) -> bytes:
    """What a browser does with a push message (RFC 8291 section 3.4), written independently."""
    salt, size, key_len = body[:16], struct.unpack(">I", body[16:20])[0], body[20]
    sender = body[21 : 21 + key_len]
    assert size == 4096
    receiver = _private(UA_PRIVATE)
    shared = receiver.exchange(
        ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), sender)
    )
    ua_public = b64url_decode(UA_PUBLIC)
    ikm = HKDF(
        hashes.SHA256(), 32, b64url_decode(AUTH), b"WebPush: info\x00" + ua_public + sender
    ).derive(shared)
    key = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    record = AESGCM(key).decrypt(nonce, body[21 + key_len :], None)
    assert record.endswith(b"\x02")
    return record[:-1]


def test_a_message_decrypts_in_the_browser() -> None:
    body = encrypt("Ciao, è finito il tempo".encode(), UA_PUBLIC, AUTH)
    assert decrypt(body).decode() == "Ciao, è finito il tempo"


def test_the_header_carries_salt_record_size_and_the_sender_key() -> None:
    body = encrypt(
        b"When I grow up, I want to be a watermelon",
        UA_PUBLIC,
        AUTH,
        salt=SALT,
        server_key=_private(AS_PRIVATE),
    )
    assert body[:16] == SALT
    assert body[16:20] == (4096).to_bytes(4, "big")
    assert body[20] == 65
    assert b64url_encode(body[21:86]) == AS_PUBLIC
    assert decrypt(body) == b"When I grow up, I want to be a watermelon"


def test_every_message_uses_a_fresh_salt_and_key() -> None:
    first, second = encrypt(b"x", UA_PUBLIC, AUTH), encrypt(b"x", UA_PUBLIC, AUTH)
    assert first[:16] != second[:16] and first[21:86] != second[21:86]


def test_an_oversized_payload_is_refused() -> None:
    with pytest.raises(ValueError):
        encrypt(b"x" * 4000, UA_PUBLIC, AUTH)


def test_vapid_keys_survive_a_pem_round_trip() -> None:
    keys = VapidKeys.generate()
    assert VapidKeys.from_pem(keys.to_pem()).public_key == keys.public_key
    assert len(b64url_decode(keys.public_key)) == 65
    assert "PRIVATE" not in repr(keys)


def test_a_non_p256_pem_is_refused() -> None:
    other = ec.generate_private_key(ec.SECP384R1())
    from cryptography.hazmat.primitives import serialization

    pem = other.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    with pytest.raises(ValueError):
        VapidKeys.from_pem(pem)


def test_the_vapid_header_is_a_valid_signed_token() -> None:
    keys = VapidKeys.generate()
    header = keys.authorization(ENDPOINT, now=1_000_000)
    scheme, rest = header.split(" ", 1)
    token, key = (part.split("=", 1)[1] for part in rest.split(", "))
    assert scheme == "vapid" and key == keys.public_key
    head, claims, signature = token.split(".")
    assert json.loads(b64url_decode(head)) == {"typ": "JWT", "alg": "ES256"}
    assert json.loads(b64url_decode(claims)) == {
        "aud": "https://push.example.net",
        "exp": 1_000_000 + 12 * 3600,
        "sub": "https://github.com/tvbalance/tvbalance",
    }
    raw = b64url_decode(signature)
    assert len(raw) == 64
    public = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), b64url_decode(keys.public_key)
    )
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    public.verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))


def _sender(status: int | Exception, seen: list[httpx.Request]) -> WebPushSender:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WebPushSender(VapidKeys.generate(), client)


TARGET = PushTarget(ENDPOINT, UA_PUBLIC, AUTH)


async def test_a_delivered_message_carries_the_push_headers() -> None:
    seen: list[httpx.Request] = []
    sender = _sender(201, seen)
    result = await sender.send(TARGET, b"hello", ttl=300, urgency="high")
    await sender.close()
    assert result is SendResult.DELIVERED
    (request,) = seen
    assert request.headers["content-encoding"] == "aes128gcm"
    assert request.headers["ttl"] == "300" and request.headers["urgency"] == "high"
    assert request.headers["authorization"].startswith("vapid t=")
    assert decrypt(request.content) == b"hello"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, SendResult.GONE),
        (410, SendResult.GONE),
        (429, SendResult.FAILED),
        (500, SendResult.FAILED),
    ],
)
async def test_the_push_service_answer_decides_the_outcome(
    status: int, expected: SendResult
) -> None:
    sender = _sender(status, [])
    assert await sender.send(TARGET, b"x") is expected
    await sender.close()


async def test_a_network_error_is_a_failure() -> None:
    sender = _sender(httpx.ConnectError("down"), [])
    assert await sender.send(TARGET, b"x") is SendResult.FAILED
    await sender.close()


async def test_only_https_endpoints_are_used() -> None:
    seen: list[httpx.Request] = []
    sender = _sender(201, seen)
    insecure = PushTarget("http://push.example.net/x", UA_PUBLIC, AUTH)
    assert await sender.send(insecure, b"x") is SendResult.FAILED
    assert seen == []
    await sender.close()


async def test_an_unusable_subscription_key_is_a_failure() -> None:
    sender = _sender(201, [])
    assert await sender.send(PushTarget(ENDPOINT, "AAAA", AUTH), b"x") is SendResult.FAILED
    await sender.close()
