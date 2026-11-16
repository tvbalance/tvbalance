from pathlib import Path

import pytest

from tvbalance.config import ConfigError, EngineConfig


def test_defaults() -> None:
    config = EngineConfig.from_env({})
    assert config == EngineConfig(host="0.0.0.0", port=8765, web_dir=None, data_dir=Path("data"))


def test_values_come_from_the_environment() -> None:
    config = EngineConfig.from_env(
        {
            "TVBALANCE_HOST": "127.0.0.1",
            "TVBALANCE_PORT": "9000",
            "TVBALANCE_WEB_DIR": "/app/web",
            "TVBALANCE_DATA_DIR": "/data",
        }
    )
    assert config == EngineConfig("127.0.0.1", 9000, Path("/app/web"), Path("/data"))


@pytest.mark.parametrize("port", ["abc", "", "0", "65536", "-1", "80.5"])
def test_invalid_port_is_rejected_with_a_clear_message(port: str) -> None:
    with pytest.raises(ConfigError, match="TVBALANCE_PORT"):
        EngineConfig.from_env({"TVBALANCE_PORT": port})


def test_empty_paths_count_as_unset() -> None:
    config = EngineConfig.from_env({"TVBALANCE_WEB_DIR": "", "TVBALANCE_DATA_DIR": ""})
    assert config.web_dir is None
    assert config.data_dir == Path("data")
