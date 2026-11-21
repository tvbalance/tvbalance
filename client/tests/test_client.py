import asyncio
from collections.abc import Awaitable, Callable

import pytest
from fastapi import FastAPI

from tvbalance_client import (
    AuthenticationError,
    TVBalanceClient,
    TVBalanceConnectionError,
    TVBalanceError,
)


async def seed_tv(app: FastAPI) -> str:
    """Pair a TV straight in the engine's storage (the API has no pairing yet)."""
    record = await app.state.storage.tvs.add("fake", "Living room", "tv.local", {"client_key": "k"})
    return str(record.id)


async def test_health(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        assert await client.health() is True


async def test_info_is_public_and_minimal(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        info = await client.info()
    assert info.api_version == "1"


async def test_adapters_need_a_token(engine_url: str, engine_token: str) -> None:
    async with TVBalanceClient(engine_url, engine_token) as client:
        (adapter,) = await client.adapters()
    assert adapter.id == "fake"
    assert "foreground_app" in adapter.capabilities


async def test_missing_or_wrong_credentials_raise_authentication_error(
    engine_url: str, engine_token: str
) -> None:
    for token in (None, "tvb_wrong"):
        async with TVBalanceClient(engine_url, token) as client:
            with pytest.raises(AuthenticationError) as refused:
                await client.tvs()
        assert refused.value.status == 401


async def test_a_read_only_token_cannot_control(
    engine_url: str, engine_app: FastAPI, mint_token: Callable[[list[str]], Awaitable[str]]
) -> None:
    tv_id = await seed_tv(engine_app)
    token = await mint_token(["read"])
    async with TVBalanceClient(engine_url, token) as client:
        assert [tv.id for tv in await client.tvs()] == [tv_id]
        with pytest.raises(AuthenticationError) as refused:
            await client.pause(tv_id)
    assert refused.value.status == 403


async def test_tvs_are_listed_and_fetched(
    engine_url: str, engine_token: str, engine_app: FastAPI
) -> None:
    tv_id = await seed_tv(engine_app)
    async with TVBalanceClient(engine_url, engine_token) as client:
        (listed,) = await client.tvs()
        fetched = await client.tv(tv_id)
    assert listed.id == fetched.id == tv_id
    assert fetched.name == "Living room" and fetched.adapter_id == "fake"


async def test_unknown_tv_raises_not_found(engine_url: str, engine_token: str) -> None:
    async with TVBalanceClient(engine_url, engine_token) as client:
        with pytest.raises(TVBalanceError) as missing:
            await client.tv("nope")
    assert missing.value.status == 404 and missing.value.code == "not_found"


async def test_override_bonus_and_pause(
    engine_url: str, engine_token: str, engine_app: FastAPI
) -> None:
    tv_id = await seed_tv(engine_app)
    async with TVBalanceClient(engine_url, engine_token) as client:
        blocked = await client.override(tv_id, allow=False, minutes=10)
        assert blocked.allow is False
        await client.clear_override(tv_id)
        assert await client.bonus(tv_id, 15) == 15
        assert await client.bonus(tv_id, 5) == 20
        paused = await client.pause(tv_id, 5)
        assert paused.allow is False


async def test_events_start_with_the_status_of_every_tv(
    engine_url: str, engine_token: str, engine_app: FastAPI
) -> None:
    tv_id = await seed_tv(engine_app)
    await engine_app.state.supervisor.refresh()
    async with TVBalanceClient(engine_url, engine_token) as client:
        stream = client.events()
        first = await asyncio.wait_for(anext(stream), 5)
        await stream.aclose()
    assert first.type == "status" and first.tv_id == tv_id
    assert "decision" in first.payload


async def test_events_refuse_anonymous_listeners(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        with pytest.raises(AuthenticationError):
            await asyncio.wait_for(anext(client.events()), 5)


async def test_unknown_path_raises_engine_error(engine_url: str) -> None:
    async with TVBalanceClient(engine_url) as client:
        with pytest.raises(TVBalanceError, match="404"):
            await client._request("GET", "/api/v1/nope")


async def test_unreachable_engine_raises_connection_error() -> None:
    async with TVBalanceClient("http://127.0.0.1:1") as client:
        with pytest.raises(TVBalanceConnectionError):
            await client.health()
