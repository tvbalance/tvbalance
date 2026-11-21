"""Check that the version numbers agree, and that a release tag matches them.

    python scripts/check_release.py            # consistency only
    python scripts/check_release.py v0.1.0     # product release tag
    python scripts/check_release.py client-v0.1.0

Exits with 1 and prints every problem found.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Versions:
    engine: str
    engine_module: str
    addon: str
    integration: str
    client: str

    @property
    def product(self) -> str:
        return self.engine


def versions(root: Path) -> Versions:
    def toml_version(path: str) -> str:
        return tomllib.loads((root / path).read_text("utf-8"))["project"]["version"]

    init = (root / "engine/src/tvbalance/__init__.py").read_text("utf-8")
    module = re.search(r'^__version__ = "([^"]+)"', init, re.MULTILINE)
    addon = re.search(
        r'^version: "([^"]+)"',
        (root / "addon/tvbalance/config.yaml").read_text("utf-8"),
        re.MULTILINE,
    )
    manifest = json.loads(
        (root / "ha/custom_components/tvbalance/manifest.json").read_text("utf-8")
    )
    return Versions(
        engine=toml_version("engine/pyproject.toml"),
        engine_module=module.group(1) if module else "?",
        addon=addon.group(1) if addon else "?",
        integration=manifest["version"],
        client=toml_version("client/pyproject.toml"),
    )


def problems(root: Path) -> list[str]:
    found = versions(root)
    result = [
        f"{name} is {value}, the engine is {found.engine}"
        for name, value in (
            ("engine/src/tvbalance/__init__.py", found.engine_module),
            ("addon/tvbalance/config.yaml", found.addon),
            ("ha manifest.json", found.integration),
        )
        if value != found.engine
    ]
    manifest = json.loads(
        (root / "ha/custom_components/tvbalance/manifest.json").read_text("utf-8")
    )
    if manifest["requirements"] != [f"tvbalance-client=={found.client}"]:
        result.append(
            f"manifest requirements {manifest['requirements']} do not pin client {found.client}"
        )
    return result


def tag_problems(root: Path, tag: str) -> list[str]:
    found = versions(root)
    if match := re.fullmatch(r"client-v(\d+\.\d+\.\d+)", tag):
        expected, label = found.client, "client"
    elif match := re.fullmatch(r"v(\d+\.\d+\.\d+)", tag):
        expected, label = found.product, "product"
    else:
        return [f"tag {tag!r} is neither vX.Y.Z nor client-vX.Y.Z"]
    if match.group(1) != expected:
        return [f"tag {tag} does not match the {label} version {expected}"]
    return problems(root)


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    found = tag_problems(root, argv[0]) if argv else problems(root)
    for line in found:
        print(f"check_release: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
