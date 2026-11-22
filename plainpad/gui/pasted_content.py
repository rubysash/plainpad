"""What a paste or a drop holds, read for the pictures in it.

The clipboard and a drag both arrive as a QMimeData that may describe an
image several ways at once. PastedContent answers which of them are there.
"""

from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QMimeData
from PyQt6.QtGui import QImage

from plainpad.config import (
    BITMAP_SAVE_FORMAT,
    IMAGE_FETCH_SCHEMES,
    IMAGE_FILE_EXTENSIONS,
)
from plainpad.rich_import import sole_image_address


class PastedContent:
    """The images offered by one paste or drop."""

    def __init__(self, mime: QMimeData) -> None:
        """Wrap the data of a paste or drop; it is not copied.

        Use the object only while the paste or drop is being handled,
        because Qt owns the data and frees it afterwards.
        """
        self._mime = mime

    def image_files(self) -> list[Path]:
        """Return the local files that are images, going by extension."""
        return [
            Path(url.toLocalFile())
            for url in self._mime.urls()
            if url.isLocalFile()
            and Path(url.toLocalFile()).suffix.lower()
            in IMAGE_FILE_EXTENSIONS
        ]

    def image_address(self) -> str | None:
        """Return the address the image was copied or dragged from.

        A browser gives this as HTML holding just the picture, or as a
        web link to an image file. Fetching the address, instead of
        taking the bitmap, is what keeps an animated GIF animated.
        """
        if self._mime.hasHtml():
            address = sole_image_address(self._mime.html())
            if address is not None:
                return address
        for url in self._mime.urls():
            is_image = Path(url.path()).suffix.lower() in IMAGE_FILE_EXTENSIONS
            if url.scheme() in IMAGE_FETCH_SCHEMES and is_image:
                return url.toString()
        return None

    def bitmap(self) -> bytes | None:
        """Return the raw picture as PNG bytes, or None if there is none.

        A screenshot arrives this way: pixels with no file behind them.
        """
        if not self._mime.hasImage():
            return None
        image = QImage(self._mime.imageData())
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if image.isNull() or not image.save(buffer, BITMAP_SAVE_FORMAT):
            return None
        return bytes(buffer.data())

    def offers_images(self) -> bool:
        """Return True if this should be pasted as images, not as text.

        A bitmap alone does not decide it: spreadsheets put a picture of
        the copied cells beside their text, and that text is what the
        user wants.
        """
        if self.image_files() or self.image_address() is not None:
            return True
        return self._mime.hasImage() and not self._mime.hasText()
