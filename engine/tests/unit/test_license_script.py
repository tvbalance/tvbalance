from __future__ import annotations

import importlib.util
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tvbalance.infra.licensing import verify_license

ROOT = Path(__file__).resolve().parents[3]


def _load():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("license_script", ROOT / "scripts/license.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["license_script"] = module
    spec.loader.exec_module(module)
    return module


script = _load()


def test_keygen_then_sign(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert script.main(["keygen", "--out", str(tmp_path)]) == 0
    public = capsys.readouterr().out.strip().splitlines()[-1]
    private = tmp_path / "license-private.pem"
    assert private.is_file()
    if sys.platform != "win32":
        assert stat.S_IMODE(private.stat().st_mode) == 0o600

    code = script.main(
        ["sign", "--private-key", str(private), "--licensee", "Rossi", "--expires", "2030-01-01"]
    )
    assert code == 0
    payload = verify_license(capsys.readouterr().out.strip(), (public,))
    assert payload.licensee == "Rossi"
    assert payload.expires_at == datetime(2030, 1, 1, tzinfo=UTC)
    assert payload.license_id


def test_sign_without_expiry_is_perpetual(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script.main(["keygen", "--out", str(tmp_path)])
    public = capsys.readouterr().out.strip().splitlines()[-1]
    script.main(
        [
            "sign",
            "--private-key",
            str(tmp_path / "license-private.pem"),
            "--licensee",
            "Rossi",
            "--license-id",
            "fixed-id",
        ]
    )
    payload = verify_license(capsys.readouterr().out.strip(), (public,))
    assert payload.expires_at is None
    assert payload.license_id == "fixed-id"


def test_keygen_never_overwrites(tmp_path: Path) -> None:
    script.main(["keygen", "--out", str(tmp_path)])
    assert script.main(["keygen", "--out", str(tmp_path)]) == 1


def test_sign_rejects_a_bad_date(tmp_path: Path) -> None:
    script.main(["keygen", "--out", str(tmp_path)])
    code = script.main(
        [
            "sign",
            "--private-key",
            str(tmp_path / "license-private.pem"),
            "--licensee",
            "Rossi",
            "--expires",
            "soon",
        ]
    )
    assert code == 1
