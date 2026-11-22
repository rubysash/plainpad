"""Tiny image files and a network stand-in shared by the image tests."""

import base64
import io
from typing import BinaryIO
from urllib.request import Request

# A real one pixel PNG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)
# Only the opening bytes matter to the app, which never decodes images.
GIF = b"GIF89a" + b"\x01\x00\x01\x00\x00\x00\x00;"
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg body"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 body"
NOT_AN_IMAGE = b"just some text"

PNG_DATA_ADDRESS = "data:image/png;base64," + base64.b64encode(PNG).decode()


class FakeWeb:
    """Stands in for urllib's urlopen, serving bytes from a dictionary.

    An address that is not in the dictionary fails like an unreachable
    server. Every address asked for is recorded.
    """

    def __init__(self, pages: dict[str, bytes]) -> None:
        """Remember what each address serves."""
        self._pages = pages
        self.requested: list[str] = []

    def __call__(self, request: Request, timeout: float) -> BinaryIO:
        """Return the bytes for the request's address as a stream."""
        address = request.full_url
        self.requested.append(address)
        if address not in self._pages:
            raise OSError("unreachable")
        return io.BytesIO(self._pages[address])
