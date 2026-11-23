"""MkDocs hook: make the Engine's OpenAPI document available next to the API reference page."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def on_pre_build(config: object) -> None:
    target = ROOT / "docs" / "developers" / "openapi.json"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "engine" / "openapi.json", target)
