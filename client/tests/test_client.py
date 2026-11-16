import pytest

from tvbalance_client import TVBalanceClient, TVBalanceConnectionError, TVBalanceError


async def test_health(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        assert await client.health() is True


async def test_info_parses_adapters(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        info = await client.info()
    assert info.api_version == "1"
    (adapter,) = info.adapters
    assert adapter.id == "fake"
    assert "foreground_app" in adapter.capabilities


async def test_unknown_path_raises_engine_error(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        with pytest.raises(TVBalanceError, match="404"):
            await client._get("/api/v1/nope")


async def test_unreachable_engine_raises_connection_error() -> None:
    async with TVBalanceClient("http://127.0.0.1:1") as client:
        with pytest.raises(TVBalanceConnectionError):
            await client.health()
