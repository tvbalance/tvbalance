from pathlib import Path

from fastapi.testclient import TestClient
from support import FAST, ScriptedTV, eventually, plugin_for, watching

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig


def test_storage_is_opened_at_startup_and_closed_at_shutdown(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    app = create_app(plugins={}, config=config)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert (config.data_dir / "tvbalance.db").is_file()
        assert (config.data_dir / "secret.key").is_file()
        assert app.state.storage is not None


def test_data_written_in_one_run_is_there_in_the_next(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    app = create_app(plugins={}, config=config)
    with TestClient(app) as client:
        assert client.portal is not None
        client.portal.call(app.state.storage.settings.set, "language", "it")

    again = create_app(plugins={}, config=config)
    with TestClient(again) as client:
        assert client.portal is not None
        value = client.portal.call(again.state.storage.settings.get, "language")
    assert value == "it"


def test_without_a_config_no_storage_is_opened(tmp_path: Path) -> None:
    app = create_app(plugins={})
    with TestClient(app):
        assert not hasattr(app.state, "storage")


def test_the_supervisor_watches_paired_tvs_while_the_app_runs(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    tv = ScriptedTV(observation=watching())
    app = create_app(plugins={"fake": plugin_for(tv)}, config=config, supervisor_settings=FAST)
    with TestClient(app) as client:
        assert client.portal is not None
        record = client.portal.call(app.state.storage.tvs.add, "fake", "TV", "tv.local", {})
        client.portal.call(app.state.supervisor.refresh)
        client.portal.call(eventually, lambda: tv.observe_calls > 0)
        status = app.state.supervisor.status(record.id)
        assert status is not None and status.connected
        assert app.state.events is not None
    assert not tv.connected  # stopped with the app


def test_no_discovery_runs_outside_an_addon(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    app = create_app(plugins={}, config=config)
    with TestClient(app):
        assert app.state.ha_discovery is None


def test_discovery_starts_and_stops_with_the_app_inside_an_addon(tmp_path: Path) -> None:
    config = EngineConfig(
        data_dir=tmp_path / "data",
        supervisor_token="t",
        supervisor_url="http://127.0.0.1:1",
    )
    app = create_app(plugins={}, config=config)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert app.state.ha_discovery is not None


def test_the_local_certificate_is_prepared_at_startup(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data")
    app = create_app(plugins={}, config=config)
    with TestClient(app):
        status = app.state.tls.status()
        assert status.active and status.mode == "auto"
        assert (config.data_dir / "tls" / "server.crt").is_file()


def test_https_can_be_switched_off(tmp_path: Path) -> None:
    config = EngineConfig(data_dir=tmp_path / "data", tls_mode="off")
    app = create_app(plugins={}, config=config)
    with TestClient(app):
        assert not app.state.tls.status().active
        assert not (config.data_dir / "tls").exists()
