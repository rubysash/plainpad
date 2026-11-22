"""Read an image's bytes from wherever a clipboard says it is.

Other programs describe a copied picture by address: embedded in the
address itself (``data:``), a temporary file (``file:``), or a web
address. This module turns any of those into bytes.
"""

import base64
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
from urllib.parse import unquote_to_bytes, urlsplit
from urllib.request import Request, url2pathname, urlopen

from plainpad.config import (
    IMAGE_FETCH_SCHEMES,
    IMAGE_FETCH_TIMEOUT_S,
    IMAGE_FETCH_USER_AGENT,
    IMAGE_MAX_BYTES,
)

DATA_SCHEME = "data"
FILE_SCHEME = "file"
BASE64_MARKER = ";base64"


class ImageSourceError(Exception):
    """An address could not be read: unknown kind, missing, or too big."""


class ImageSourceReader:
    """Fetches the bytes behind an image address."""

    def __init__(
        self, open_url: Callable[..., BinaryIO] = urlopen
    ) -> None:
        """Remember how web addresses are opened.

        ``open_url`` is called like urllib's urlopen. Tests pass a
        stand-in so they never touch the network.
        """
        self._open_url = open_url

    def read(
        self, address: str, timeout: float = IMAGE_FETCH_TIMEOUT_S
    ) -> bytes:
        """Return the bytes at ``address``.

        ``timeout`` is in seconds and only applies to web addresses.
        Raises ImageSourceError if the address is of a kind that cannot
        be read (such as an email's ``cid:``), cannot be reached, or
        holds more than config.IMAGE_MAX_BYTES.
        """
        scheme = urlsplit(address).scheme.lower()
        try:
            if scheme == DATA_SCHEME:
                return self.read_embedded(address)
            if scheme == FILE_SCHEME:
                return self.read_file(address)
            if scheme in IMAGE_FETCH_SCHEMES:
                return self.read_web(address, timeout)
        except (OSError, ValueError) as error:
            raise ImageSourceError(str(error)) from error
        raise ImageSourceError(f"Cannot read a '{scheme}' address.")

    def read_embedded(self, address: str) -> bytes:
        """Decode a ``data:`` address, base64 or percent-encoded."""
        header, _, payload = address.partition(",")
        if header.lower().endswith(BASE64_MARKER):
            return base64.b64decode(payload)
        return unquote_to_bytes(payload)

    def read_file(self, address: str) -> bytes:
        """Read the local file a ``file:`` address names."""
        path = Path(url2pathname(urlsplit(address).path))
        if path.stat().st_size > IMAGE_MAX_BYTES:
            raise ValueError("The image is too large.")
        return path.read_bytes()

    def read_web(self, address: str, timeout: float) -> bytes:
        """Download a web address, refusing anything over the size cap."""
        request = Request(
            address, headers={"User-Agent": IMAGE_FETCH_USER_AGENT}
        )
        with self._open_url(request, timeout=timeout) as response:
            # One byte past the cap is enough to know it is too large.
            data = response.read(IMAGE_MAX_BYTES + 1)
        if len(data) > IMAGE_MAX_BYTES:
            raise ValueError("The image is too large.")
        return data
