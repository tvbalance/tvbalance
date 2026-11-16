import asyncio

import pytest

from tvbalance.app.session import SessionTimeouts, TVSession
from tvbalance.domain.models import GoHome
from tvbalance.sdk.errors import TVError, TVTimeoutError
from tvbalance.sdk.fake import FakeTV


async def test_observe_returns_adapter_observation() -> None:
    tv = FakeTV()
    session = TVSession(tv)
    await session.connect()
    assert (await session.observe()) == tv.observation


async def test_hung_observe_hits_the_hard_timeout() -> None:
    tv = FakeTV(hang_observe=True)
    session = TVSession(tv, SessionTimeouts(observe=0.05))
    await session.connect()
    with pytest.raises(TVTimeoutError):
        await session.observe()


async def test_hung_call_does_not_block_other_work() -> None:
    tv = FakeTV(hang_observe=True)
    session = TVSession(tv, SessionTimeouts(observe=0.05))
    await session.connect()
    results = await asyncio.gather(session.observe(), session.list_apps(), return_exceptions=True)
    assert isinstance(results[0], TVTimeoutError)
    assert results[1] == tv.apps


async def test_adapter_errors_stay_typed() -> None:
    tv = FakeTV(fail_execute=True)
    session = TVSession(tv)
    with pytest.raises(TVError):
        await session.execute(GoHome())


async def test_unexpected_exceptions_are_mapped_to_tverror() -> None:
    class Broken(FakeTV):
        async def list_apps(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    session = TVSession(Broken())
    with pytest.raises(TVError, match="RuntimeError"):
        await session.list_apps()


async def test_observe_before_connect_fails_typed() -> None:
    session = TVSession(FakeTV())
    with pytest.raises(TVError):
        await session.observe()
