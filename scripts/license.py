"""Create the license signing key and issue Pro license keys.

    uv run python scripts/license.py keygen --out DIR
    uv run python scripts/license.py sign --private-key DIR/license-private.pem --licensee NAME
        [--expires YYYY-MM-DD] [--license-id ID]

Keep the private key offline, outside the repository. ``keygen`` prints the public key to add to
``TRUSTED_PUBLIC_KEYS`` in ``engine/src/tvbalance/infra/licensing.py``; ``sign`` prints a
license key.
Exits with 1 and prints the problem on failure.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from tvbalance.infra.licensing import PAYLOAD_VERSION, PRODUCT, TIER, generate_keypair, sign_license

PRIVATE_NAME = "license-private.pem"


def keygen(out: Path) -> str:
    target = out / PRIVATE_NAME
    if target.exists():
        raise SystemExit(f"{target} already exists: refusing to overwrite a signing key")
    out.mkdir(parents=True, exist_ok=True)
    private, public = generate_keypair()
    target.write_bytes(private)
    with contextlib.suppress(OSError):
        os.chmod(target, 0o600)
    return public


def issue(private_key: Path, licensee: str, expires: str | None, license_id: str | None) -> str:
    expires_at = None
    if expires:
        try:
            expires_at = datetime.fromisoformat(expires).replace(tzinfo=UTC).isoformat()
        except ValueError:
            raise SystemExit(f"--expires must be a date like 2030-01-31, got {expires!r}") from None
    payload = {
        "v": PAYLOAD_VERSION,
        "product": PRODUCT,
        "tier": TIER,
        "license_id": license_id or str(uuid.uuid4()),
        "licensee": licensee,
        "issued_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "expires_at": expires_at,
    }
    return sign_license(payload, private_key.read_bytes())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])  # type: ignore[union-attr]
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("keygen", help="create the signing key pair")
    gen.add_argument("--out", type=Path, required=True)
    sign = commands.add_parser("sign", help="issue a license key")
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--licensee", required=True)
    sign.add_argument(
        "--expires", help="expiry date (00:00 UTC of that day), YYYY-MM-DD; default perpetual"
    )
    sign.add_argument("--license-id")
    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            print(keygen(args.out))
        else:
            print(issue(args.private_key, args.licensee, args.expires, args.license_id))
    except SystemExit as stop:
        print(f"license: {stop}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
