"""Find LG TVs on the local network with SSDP."""

from __future__ import annotations

import asyncio

from tvbalance.sdk.types import DiscoveredDevice

SEARCH_TARGET = "urn:lge-com:service:webos-second-screen:1"
MULTICAST = ("239.255.255.250", 1900)
WINDOW = 3.0  # seconds spent listening for answers: a search, not a TV call

_REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {MULTICAST[0]}:{MULTICAST[1]}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 2\r\n"
    f"ST: {SEARCH_TARGET}\r\n\r\n"
).encode()


def parse_response(data: bytes) -> str | None:
    """The search target a reply announces, when it is an LG webOS TV answer."""
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return None
    if not lines or not lines[0].upper().startswith("HTTP/"):
        return None
    for line in lines[1:]:
        name, _, value = line.partition(":")
        if name.strip().upper() == "ST" and value.strip().lower() == SEARCH_TARGET:
            return SEARCH_TARGET
    return None


class _Collector(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.hosts: list[str] = []

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if parse_response(data) and addr[0] not in self.hosts:
            self.hosts.append(addr[0])


async def discover(
    target: tuple[str, int] = MULTICAST, window: float = WINDOW
) -> list[DiscoveredDevice]:
    """TVs that answered an SSDP search within ``window`` seconds, one per address."""
    loop = asyncio.get_running_loop()
    transport, collector = await loop.create_datagram_endpoint(
        _Collector, local_addr=("0.0.0.0", 0)
    )
    try:
        transport.sendto(_REQUEST, target)
        await asyncio.sleep(window)
    finally:
        transport.close()
    return [DiscoveredDevice("webos", host, "LG webOS TV") for host in collector.hosts]
