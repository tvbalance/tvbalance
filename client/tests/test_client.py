import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from cryptography import x509
from fastapi import FastAPI

from tvbalance.infra import tls
from tvbalance_client import (
    AuthenticationError,
    CertificateError,
    TVBalanceClient,
    TVBalanceConnectionError,
    TVBalanceError,
    ca_fingerprint,
    fetch_ca_certificate,
    parse_status,
    ssl_context_for,
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


async def test_status_carries_input_channel_and_program(
    engine_url: str, engine_token: str, engine_app: FastAPI
) -> None:
    tv_id = await seed_tv(engine_app)
    await engine_app.state.supervisor.refresh()
    async with TVBalanceClient(engine_url, engine_token) as client:
        tv = await client.tv(tv_id)
    assert tv.status is not None
    assert tv.status.input_id is None or isinstance(tv.status.input_id, str)
    assert tv.status.channel_id is None or isinstance(tv.status.channel_id, str)
    assert tv.status.program_title is None or isinstance(tv.status.program_title, str)


async def test_me_reports_the_token_scopes(
    engine_url: str, mint_token: Callable[[list[str]], Awaitable[str]]
) -> None:
    token = await mint_token(["read", "control"])
    async with TVBalanceClient(engine_url, token) as client:
        me = await client.me()
    assert me.kind == "token"
    assert set(me.scopes) == {"read", "control"}


async def test_update_tv_needs_the_admin_scope(
    engine_url: str, engine_app: FastAPI, mint_token: Callable[[list[str]], Awaitable[str]]
) -> None:
    tv_id = await seed_tv(engine_app)
    control = await mint_token(["read", "control"])
    async with TVBalanceClient(engine_url, control) as client:
        with pytest.raises(AuthenticationError) as refused:
            await client.update_tv(tv_id, enabled=False)
    assert refused.value.status == 403
    admin = await mint_token(["read", "control", "admin"])
    async with TVBalanceClient(engine_url, admin) as client:
        off = await client.update_tv(tv_id, enabled=False, name="Den")
        assert off.enabled is False and off.name == "Den"
        assert (await client.update_tv(tv_id, enabled=True)).enabled is True


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
    assert parse_status(first.payload).connected in (True, False)


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


async def test_the_ca_is_fetched_and_fingerprinted(https_url: str) -> None:
    pem = await fetch_ca_certificate(https_url)
    assert pem.startswith("-----BEGIN CERTIFICATE-----")
    assert ca_fingerprint(pem) == tls.fingerprint(x509.load_pem_x509_certificate(pem.encode()))


async def test_a_pinned_ca_opens_the_secure_connection(https_url: str) -> None:
    context = ssl_context_for(await fetch_ca_certificate(https_url))
    async with TVBalanceClient(https_url, ssl_context=context) as client:
        assert await client.health() is True


async def test_an_unknown_ca_is_a_certificate_error(https_url: str) -> None:
    async with TVBalanceClient(https_url) as client:
        with pytest.raises(CertificateError):
            await client.health()


async def test_another_ca_is_a_certificate_error(https_url: str) -> None:
    other = tls.ca_cert_pem(tls.create_ca(datetime.now(UTC))).decode()
    async with TVBalanceClient(https_url, ssl_context=ssl_context_for(other)) as client:
        with pytest.raises(CertificateError):
            await client.health()


async def test_the_event_stream_uses_the_pinned_ca(https_url: str) -> None:
    context = ssl_context_for(await fetch_ca_certificate(https_url))
    async with TVBalanceClient(https_url, ssl_context=context) as client:
        with pytest.raises(AuthenticationError):  # reaching the sign-in check means TLS worked
            await asyncio.wait_for(anext(client.events()), 5)
