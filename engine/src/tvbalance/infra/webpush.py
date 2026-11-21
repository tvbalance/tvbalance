"""Web Push: VAPID (RFC 8292) and aes128gcm payload encryption (RFC 8291, RFC 8188)."""

from __future__ import annotations

import base64
import json
import logging
import os
import struct
import time
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger(__name__)

VAPID_SUBJECT = "https://github.com/tvbalance/tvbalance"
VAPID_LIFETIME = 12 * 3600
RECORD_SIZE = 4096
MAX_PAYLOAD = 3800
SEND_TIMEOUT = 15.0


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _point(public: ec.EllipticCurvePublicKey) -> bytes:
    return public.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


class VapidKeys:
    """The Engine's application server key pair (P-256)."""

    def __init__(self, private: ec.EllipticCurvePrivateKey) -> None:
        self._private = private

    def __repr__(self) -> str:
        return "VapidKeys()"

    @classmethod
    def generate(cls) -> VapidKeys:
        return cls(ec.generate_private_key(ec.SECP256R1()))

    @classmethod
    def from_pem(cls, pem: str) -> VapidKeys:
        key = serialization.load_pem_private_key(pem.encode("ascii"), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
            raise ValueError("the VAPID key must be a P-256 private key")
        return cls(key)

    def to_pem(self) -> str:
        return self._private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii")

    @property
    def public_key(self) -> str:
        """The `applicationServerKey` a browser subscribes with."""
        return b64url_encode(_point(self._private.public_key()))

    def authorization(self, endpoint: str, now: float | None = None) -> str:
        parts = urlsplit(endpoint)
        claims = {
            "aud": f"{parts.scheme}://{parts.netloc}",
            "exp": int((time.time() if now is None else now) + VAPID_LIFETIME),
            "sub": VAPID_SUBJECT,
        }
        header = {"typ": "JWT", "alg": "ES256"}
        signing_input = ".".join(
            b64url_encode(json.dumps(part, separators=(",", ":")).encode())
            for part in (header, claims)
        )
        r, s = decode_dss_signature(
            self._private.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
        )
        signature = b64url_encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        return f"vapid t={signing_input}.{signature}, k={self.public_key}"


def encrypt(
    payload: bytes,
    p256dh: str,
    auth: str,
    *,
    salt: bytes | None = None,
    server_key: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """The request body for one push message. ``salt`` and ``server_key`` exist for tests."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"a push payload may not exceed {MAX_PAYLOAD} bytes")
    receiver = b64url_decode(p256dh)
    secret = b64url_decode(auth)
    salt = salt if salt is not None else os.urandom(16)
    server = server_key or ec.generate_private_key(ec.SECP256R1())
    sender = _point(server.public_key())
    shared = server.exchange(
        ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), receiver)
    )

    def derive(length: int, key_salt: bytes, info: bytes, material: bytes) -> bytes:
        return HKDF(hashes.SHA256(), length, key_salt, info).derive(material)

    ikm = derive(32, secret, b"WebPush: info\x00" + receiver + sender, shared)
    key = derive(16, salt, b"Content-Encoding: aes128gcm\x00", ikm)
    nonce = derive(12, salt, b"Content-Encoding: nonce\x00", ikm)
    sealed = AESGCM(key).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack(">IB", RECORD_SIZE, len(sender)) + sender + sealed


@dataclass(frozen=True, slots=True)
class PushTarget:
    endpoint: str
    p256dh: str
    auth: str


class SendResult(StrEnum):
    DELIVERED = "delivered"
    GONE = "gone"  # the push service forgot the subscription: remove it
    FAILED = "failed"  # try again later


class WebPushSender:
    def __init__(self, keys: VapidKeys, client: httpx.AsyncClient | None = None) -> None:
        self._keys = keys
        self._client = client or httpx.AsyncClient(timeout=SEND_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    async def send(
        self, target: PushTarget, payload: bytes, *, ttl: int = 3600, urgency: str = "normal"
    ) -> SendResult:
        if urlsplit(target.endpoint).scheme != "https":
            return SendResult.FAILED
        try:
            body = encrypt(payload, target.p256dh, target.auth)
            response = await self._client.post(
                target.endpoint,
                content=body,
                headers={
                    "Content-Encoding": "aes128gcm",
                    "Content-Type": "application/octet-stream",
                    "TTL": str(ttl),
                    "Urgency": urgency,
                    "Authorization": self._keys.authorization(target.endpoint),
                },
            )
        except (httpx.HTTPError, ValueError) as ex:
            log.warning("push delivery failed: %s", type(ex).__name__)
            return SendResult.FAILED
        if response.is_success:
            return SendResult.DELIVERED
        if response.status_code in (404, 410):
            return SendResult.GONE
        log.warning("push service answered %s", response.status_code)
        return SendResult.FAILED
