import asyncio
from collections.abc import AsyncIterator

import pytest

from tvbalance.sdk.types import DiscoveredDevice
from tvbalance_adapter_webos.discovery import SEARCH_TARGET, discover, parse_response


def _reply(st: str = SEARCH_TARGET) -> bytes:
    return (
        f"HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=1800\r\nST: {st}\r\n"
        "USN: uuid:abc::urn:lge-com:service:webos-second-screen:1\r\n"
        "SERVER: Linux/4.4 UPnP/1.0 LGE WebOS TV\r\n\r\n"
    ).encode()


class _Responder(asyncio.DatagramProtocol):
    def __init__(self, replies: list[bytes]) -> None:
        self.replies = replies
        self.requests: list[bytes] = []
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.requests.append(data)
        for reply in self.replies:
            assert self.transport is not None
            self.transport.sendto(reply, addr)


async def _serve(replies: list[bytes]) -> tuple[_Responder, tuple[str, int], AsyncIterator[None]]:
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(
        lambda: _Responder(replies), local_addr=("127.0.0.1", 0)
    )
    port = transport.get_extra_info("sockname")[1]

    async def closer() -> AsyncIterator[None]:
        yield
        transport.close()

    return proto, ("127.0.0.1", port), closer()


async def test_finds_a_tv_and_deduplicates_replies() -> None:
    proto, target, closer = await _serve([_reply(), _reply()])
    found = await discover(target=target, window=0.3)
    await anext(closer)
    assert found == [DiscoveredDevice("webos", "127.0.0.1", "LG webOS TV")]
    assert b"M-SEARCH" in proto.requests[0]
    assert SEARCH_TARGET.encode() in proto.requests[0]


async def test_ignores_other_devices() -> None:
    _, target, closer = await _serve([_reply("urn:schemas-upnp-org:device:MediaRenderer:1")])
    assert await discover(target=target, window=0.3) == []
    await anext(closer)


async def test_nobody_answering_is_an_empty_list() -> None:
    _, target, closer = await _serve([])
    assert await discover(target=target, window=0.2) == []
    await anext(closer)


@pytest.mark.parametrize("garbage", [b"", b"\xff\xfe", b"not http at all"])
def test_garbage_replies_are_ignored(garbage: bytes) -> None:
    assert parse_response(garbage) is None


def test_parse_is_case_insensitive() -> None:
    assert parse_response(_reply().lower()) is not None
