"""Entry point: `python -m tvbalance` or the `tvbalance` script."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from tvbalance.api.app import create_app


def main() -> None:
    host = os.environ.get("TVBALANCE_HOST", "0.0.0.0")
    port = int(os.environ.get("TVBALANCE_PORT", "8765"))
    web_dir = Path(os.environ["TVBALANCE_WEB_DIR"]) if "TVBALANCE_WEB_DIR" in os.environ else None
    uvicorn.run(create_app(web_dir=web_dir), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
