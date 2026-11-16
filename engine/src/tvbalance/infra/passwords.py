"""Hashing of the admin password and PIN (argon2id)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_secret(secret: str) -> str:
    return _hasher.hash(secret)


def verify_secret(stored_hash: str, secret: str) -> bool:
    try:
        return _hasher.verify(stored_hash, secret)
    except (VerificationError, InvalidHashError):
        return False
