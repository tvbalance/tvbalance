import asyncio
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from support import FAST, FakeClock, ScriptedTV, plugin_for, seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.app.pairing import PairingService
from tvbalance.config import EngineConfig
from tvbalance.sdk.plugin import AdapterPlugin
from tvbalance.sdk.types import DiscoveredDevice


def with_discovery(plugin: AdapterPlugin, *devices: DiscoveredDevice) -> AdapterPlugin:
    async def discover() -> list[DiscoveredDevice]:
        return list(devices)

    return AdapterPlugin(plugin.info, plugin.factory, discover)


def start(
    engine_config: EngineConfig, plugins: dict[str, AdapterPlugin], **options: object
) -> Iterator[TestClient]:
    app = create_app(
        plugins=plugins,
        include_testing=True,
        config=engine_config,
        clock=FakeClock(),
        supervisor_settings=FAST,
        **options,  # type: ignore[arg-type]
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


@pytest.fixture
def client(engine_config: EngineConfig) -> Iterator[TestClient]:
    found = with_discovery(
        plugin_for(ScriptedTV()),
        DiscoveredDevice("fake", "10.0.0.5", "Bedroom", "model-x"),
        DiscoveredDevice("fake", "10.0.0.5", "Bedroom again"),
        DiscoveredDevice("fake", "tv.local", "Living room"),
    )
    yield from start(engine_config, {"fake": found})


def test_discovery_lists_found_tvs_once_per_address(client: TestClient) -> None:
    body = client.get("/api/v1/discovery").json()
    assert [(d["host"], d["name"]) for d in body] == [
        ("10.0.0.5", "Bedroom"),
        ("tv.local", "Living room"),
    ]
    assert body[0]["adapter_id"] == "fake"
    assert body[0]["adapter_name"] == "Fake TV"
    assert body[0]["model"] == "model-x"


def test_a_tv_that_is_already_added_is_flagged(client: TestClient) -> None:
    seed_tv(client, host="tv.local")
    body = client.get("/api/v1/discovery").json()
    assert {d["host"]: d["already_added"] for d in body} == {"10.0.0.5": False, "tv.local": True}


def test_a_failing_or_slow_adapter_does_not_hide_the_others(engine_config: EngineConfig) -> None:
    async def broken() -> list[DiscoveredDevice]:
        raise OSError("no multicast")

    async def slow() -> list[DiscoveredDevice]:
        await asyncio.Event().wait()
        return []

    good = with_discovery(plugin_for(ScriptedTV()), DiscoveredDevice("fake", "10.0.0.5", "Bedroom"))
    bad = plugin_for(ScriptedTV(), adapter_id="broken")
    hung = plugin_for(ScriptedTV(), adapter_id="hung")
    plugins = {
        "fake": good,
        "broken": AdapterPlugin(bad.info, bad.factory, broken),
        "hung": AdapterPlugin(hung.info, hung.factory, slow),
        "silent": plugin_for(ScriptedTV(), adapter_id="silent"),
    }
    app = create_app(
        plugins=plugins,
        include_testing=True,
        config=engine_config,
        clock=FakeClock(),
        supervisor_settings=FAST,
        discovery_timeout=0.1,
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        body = running.get("/api/v1/discovery").json()
    assert [d["host"] for d in body] == ["10.0.0.5"]


def test_testing_adapters_are_not_searched_unless_enabled(engine_config: EngineConfig) -> None:
    plugin = with_discovery(plugin_for(ScriptedTV()), DiscoveredDevice("fake", "x", "X"))
    object.__setattr__(plugin.info, "testing_only", True)
    app = create_app(plugins={"fake": plugin}, config=engine_config, clock=FakeClock())
    with TestClient(app) as running:
        sign_in_as_admin(running)
        assert running.get("/api/v1/discovery").json() == []


def test_concurrent_searches_share_one_scan() -> None:
    calls = 0

    async def discover() -> list[DiscoveredDevice]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return [DiscoveredDevice("fake", "10.0.0.5", "Bedroom")]

    base = plugin_for(ScriptedTV())
    plugin = AdapterPlugin(base.info, base.factory, discover)

    async def no_tvs() -> list[object]:
        return []

    async def scenario() -> None:
        storage = SimpleNamespace(tvs=SimpleNamespace(list=no_tvs))
        service = PairingService(storage, {"fake": plugin})  # type: ignore[arg-type]
        first, second = await asyncio.gather(service.discover(), service.discover())
        assert first == second and len(first) == 1

    asyncio.run(scenario())
    assert calls == 1


def test_a_pin_session_cannot_search(engine_config: EngineConfig) -> None:
    plugin = with_discovery(plugin_for(ScriptedTV()))
    gen = start(engine_config, {"fake": plugin})
    client = next(gen)
    try:
        assert client.put("/api/v1/auth/pin", json={"pin": "4821"}).status_code == 204
        client.cookies.clear()
        client.headers.pop("X-TVBalance-CSRF", None)
        assert client.post("/api/v1/auth/pin-login", json={"pin": "4821"}).status_code == 200
        assert client.get("/api/v1/discovery").status_code == 403
    finally:
        gen.close()


def test_discovery_needs_a_signed_in_caller(engine_config: EngineConfig) -> None:
    app = create_app(plugins={}, config=engine_config)
    with TestClient(app) as running:
        assert running.get("/api/v1/discovery").status_code == 401
