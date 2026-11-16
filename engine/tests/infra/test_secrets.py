import sys
from pathlib import Path

import pytest

from tvbalance.infra.secrets import SecretBox, SecretError

KEY = bytes(range(32))


def test_round_trip() -> None:
    box = SecretBox(KEY)
    assert box.decrypt(box.encrypt(b"client-key")) == b"client-key"


def test_every_encryption_uses_a_fresh_nonce() -> None:
    box = SecretBox(KEY)
    assert box.encrypt(b"same") != box.encrypt(b"same")


def test_the_plaintext_is_not_visible_in_the_blob() -> None:
    assert b"client-key" not in SecretBox(KEY).encrypt(b"client-key")


def test_wrong_key_is_an_error() -> None:
    blob = SecretBox(KEY).encrypt(b"secret")
    with pytest.raises(SecretError):
        SecretBox(bytes(32)).decrypt(blob)


def test_tampered_data_is_an_error() -> None:
    box = SecretBox(KEY)
    blob = bytearray(box.encrypt(b"secret"))
    blob[-1] ^= 1
    with pytest.raises(SecretError):
        box.decrypt(bytes(blob))


@pytest.mark.parametrize("blob", [b"", b"short"])
def test_truncated_data_is_an_error(blob: bytes) -> None:
    with pytest.raises(SecretError):
        SecretBox(KEY).decrypt(blob)


def test_key_must_have_the_right_length() -> None:
    with pytest.raises(SecretError):
        SecretBox(b"too short")


def test_json_round_trip() -> None:
    box = SecretBox(KEY)
    credentials = {"client_key": "abc", "token": "é"}
    assert box.open_json(box.seal_json(credentials)) == credentials


def test_json_of_the_wrong_shape_is_an_error() -> None:
    box = SecretBox(KEY)
    with pytest.raises(SecretError):
        box.open_json(box.encrypt(b"[1, 2]"))
    with pytest.raises(SecretError):
        box.open_json(box.encrypt(b"not json"))


def test_load_or_create_makes_the_key_once_and_reuses_it(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "secret.key"
    first = SecretBox.load_or_create(path)
    blob = first.encrypt(b"secret")
    assert path.read_bytes() != b""
    assert SecretBox.load_or_create(path).decrypt(blob) == b"secret"


def test_a_damaged_key_file_is_an_error_and_is_left_alone(tmp_path: Path) -> None:
    path = tmp_path / "secret.key"
    path.write_bytes(b"damaged")
    with pytest.raises(SecretError):
        SecretBox.load_or_create(path)
    assert path.read_bytes() == b"damaged"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_the_key_file_is_private_to_the_owner(tmp_path: Path) -> None:
    path = tmp_path / "secret.key"
    SecretBox.load_or_create(path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_repr_does_not_show_the_key() -> None:
    assert KEY.hex() not in repr(SecretBox(KEY))
    assert str(list(KEY)) not in repr(SecretBox(KEY))
