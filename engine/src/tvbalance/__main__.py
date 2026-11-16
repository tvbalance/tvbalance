"""Entry point: `python -m tvbalance` or the `tvbalance` script."""

from __future__ import annotations

import os
import sys

import uvicorn

from tvbalance.api.app import create_app
from tvbalance.config import ConfigError, EngineConfig


def main() -> None:
    try:
        config = EngineConfig.from_env(os.environ)
    except ConfigError as ex:
        sys.exit(f"tvbalance: {ex}")
    uvicorn.run(
        create_app(web_dir=config.web_dir), host=config.host, port=config.port, log_level="info"
    )


if __name__ == "__main__":
    main()
