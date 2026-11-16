"""Write the OpenAPI document to engine/openapi.json (run after changing the API)."""

from __future__ import annotations

import json
from pathlib import Path

from tvbalance.api.app import create_app

TARGET = Path(__file__).resolve().parents[1] / "openapi.json"


def render() -> str:
    # Empty plugin map: the document must not depend on which adapters are installed.
    return json.dumps(create_app(plugins={}).openapi(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    TARGET.write_text(render(), encoding="utf-8")
    print(f"wrote {TARGET}")
