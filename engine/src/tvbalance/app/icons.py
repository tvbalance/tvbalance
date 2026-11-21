"""Fetching an app icon from the TV itself, so browsers never have to reach the TV."""

from __future__ import annotations

import asyncio
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 512 * 1024
TIMEOUT = 5.0


class IconUnavailable(Exception):
    """The icon cannot be served: wrong host, not an image, too large, or the TV said no."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None  # a redirect could lead away from the TV


_opener = urllib.request.build_opener(_NoRedirects)


def _fetch(url: str) -> tuple[bytes, str]:
    try:
        with _opener.open(url, timeout=TIMEOUT) as response:
            kind = response.headers.get_content_type()
            body = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError) as ex:
        raise IconUnavailable(f"the TV did not give the icon: {ex}") from ex
    if not kind.startswith("image/"):
        raise IconUnavailable(f"the TV answered {kind}, not an image")
    if len(body) > MAX_BYTES:
        raise IconUnavailable("the icon is too large")
    return body, kind


async def fetch_icon(url: str, tv_host: str) -> tuple[bytes, str]:
    """The icon's bytes and media type. Only http(s) addresses on the TV's own host are fetched."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or parts.hostname != tv_host:
        raise IconUnavailable("the icon is not on the TV")
    return await asyncio.to_thread(_fetch, url)
