"""Encryption of secrets at rest (adapter credentials) with a locally generated key."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32
_NONCE_BYTES = 12


class SecretError(Exception):
    """A secret cannot be read: damaged data, a wrong key or a bad key file."""


class SecretBox:
    """AES-GCM with a random nonce per message; a blob is ``nonce + ciphertext + tag``."""

    __slots__ = ("_aead",)

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise SecretError(f"the key must be {KEY_BYTES} bytes long")
        self._aead = AESGCM(key)

    def __repr__(self) -> str:
        return "SecretBox()"

    @classmethod
    def load_or_create(cls, path: Path) -> SecretBox:
        """Read the key file, or make a private one on first use. A damaged file is kept."""
        try:
            return cls(path.read_bytes())
        except FileNotFoundError:
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        key = os.urandom(KEY_BYTES)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:  # another process won the race
            return cls(path.read_bytes())
        with os.fdopen(fd, "wb") as file:
            file.write(key)
        return cls(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(_NONCE_BYTES)
        return nonce + self._aead.encrypt(nonce, plaintext, None)

    def decrypt(self, blob: bytes) -> bytes:
        nonce, data = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        try:
            return self._aead.decrypt(nonce, data, None)
        except (InvalidTag, ValueError) as ex:
            raise SecretError("the secret cannot be decrypted") from ex

    def seal_json(self, values: dict[str, str]) -> bytes:
        return self.encrypt(json.dumps(values).encode())

    def open_json(self, blob: bytes) -> dict[str, str]:
        try:
            values = json.loads(self.decrypt(blob))
        except ValueError as ex:
            raise SecretError("the secret is not valid JSON") from ex
        if not isinstance(values, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in values.items()
        ):
            raise SecretError("the secret is not a string map")
        return values
