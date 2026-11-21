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


def test_ingress_is_not_trusted_unless_configured() -> None:
    assert EngineConfig.from_env({}).ingress_trusted == frozenset()
    assert EngineConfig.from_env({"TVBALANCE_INGRESS_TRUSTED": ""}).ingress_trusted == frozenset()


def test_trusted_ingress_peers_are_a_comma_separated_list() -> None:
    config = EngineConfig.from_env({"TVBALANCE_INGRESS_TRUSTED": "172.30.32.2, 10.0.0.5 ,,"})
    assert config.ingress_trusted == frozenset({"172.30.32.2", "10.0.0.5"})


@pytest.mark.parametrize("port", ["abc", "", "0", "65536", "-1", "80.5"])
def test_invalid_port_is_rejected_with_a_clear_message(port: str) -> None:
    with pytest.raises(ConfigError, match="TVBALANCE_PORT"):
        EngineConfig.from_env({"TVBALANCE_PORT": port})


def test_empty_paths_count_as_unset() -> None:
    config = EngineConfig.from_env({"TVBALANCE_WEB_DIR": "", "TVBALANCE_DATA_DIR": ""})
    assert config.web_dir is None
    assert config.data_dir == Path("data")


def test_the_supervisor_is_only_known_inside_an_addon() -> None:
    config = EngineConfig.from_env({})
    assert config.supervisor_token is None
    assert config.supervisor_url == "http://supervisor"


def test_supervisor_settings_come_from_the_environment() -> None:
    config = EngineConfig.from_env(
        {"SUPERVISOR_TOKEN": "tok", "TVBALANCE_SUPERVISOR_URL": "http://127.0.0.1:9"}
    )
    assert config.supervisor_token == "tok"
    assert config.supervisor_url == "http://127.0.0.1:9"
    assert "tok" not in repr(config)


def test_tls_defaults_to_automatic_certificates_on_8766() -> None:
    config = EngineConfig.from_env({})
    assert (config.tls_mode, config.https_port) == ("auto", 8766)
    assert config.tls_certfile is None and config.tls_keyfile is None and config.tls_names == ()


def test_tls_settings_come_from_the_environment() -> None:
    config = EngineConfig.from_env(
        {
            "TVBALANCE_TLS": "off",
            "TVBALANCE_HTTPS_PORT": "9443",
            "TVBALANCE_TLS_NAMES": "tv.local, box.lan ,",
        }
    )
    assert (config.tls_mode, config.https_port) == ("off", 9443)
    assert config.tls_names == ("tv.local", "box.lan")


def test_a_certificate_and_key_switch_to_custom_mode() -> None:
    config = EngineConfig.from_env(
        {"TVBALANCE_TLS_CERTFILE": "/ssl/fullchain.pem", "TVBALANCE_TLS_KEYFILE": "/ssl/key.pem"}
    )
    assert config.tls_mode == "custom"
    assert config.tls_certfile == Path("/ssl/fullchain.pem")
    assert config.tls_keyfile == Path("/ssl/key.pem")


def test_off_wins_over_a_certificate() -> None:
    config = EngineConfig.from_env(
        {
            "TVBALANCE_TLS": "off",
            "TVBALANCE_TLS_CERTFILE": "/ssl/a.pem",
            "TVBALANCE_TLS_KEYFILE": "/ssl/b.pem",
        }
    )
    assert config.tls_mode == "off"


@pytest.mark.parametrize("name", ["TVBALANCE_TLS_CERTFILE", "TVBALANCE_TLS_KEYFILE"])
def test_a_certificate_without_its_key_is_rejected(name: str) -> None:
    with pytest.raises(ConfigError, match="TVBALANCE_TLS_CERTFILE and TVBALANCE_TLS_KEYFILE"):
        EngineConfig.from_env({name: "/ssl/x.pem"})


def test_unknown_tls_mode_and_bad_https_port_are_rejected() -> None:
    with pytest.raises(ConfigError, match="TVBALANCE_TLS must be"):
        EngineConfig.from_env({"TVBALANCE_TLS": "maybe"})
    with pytest.raises(ConfigError, match="TVBALANCE_HTTPS_PORT"):
        EngineConfig.from_env({"TVBALANCE_HTTPS_PORT": "0"})
    with pytest.raises(ConfigError, match="different ports"):
        EngineConfig.from_env({"TVBALANCE_PORT": "9000", "TVBALANCE_HTTPS_PORT": "9000"})


def test_addon_options_fill_in_what_the_environment_leaves_out(tmp_path: Path) -> None:
    (tmp_path / "options.json").write_text(
        '{"tls": "off", "tls_certfile": "fullchain.pem", "tls_keyfile": "privkey.pem",'
        ' "tls_names": ["tv.local"]}',
        encoding="utf-8",
    )
    config = EngineConfig.from_env({"TVBALANCE_DATA_DIR": str(tmp_path)})
    assert config.tls_mode == "off" and config.tls_names == ("tv.local",)
    assert config.tls_certfile == Path("/ssl") / "fullchain.pem"
    env_wins = EngineConfig.from_env({"TVBALANCE_DATA_DIR": str(tmp_path), "TVBALANCE_TLS": "auto"})
    assert env_wins.tls_mode == "custom"


def test_unreadable_addon_options_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "options.json").write_text("not json", encoding="utf-8")
    config = EngineConfig.from_env({"TVBALANCE_DATA_DIR": str(tmp_path)})
    assert config.tls_mode == "auto"
