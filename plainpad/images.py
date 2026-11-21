"""Store the pictures that notes link to.

Every image lives in one folder and is named by a hash of its content, so
a picture used by several notes, or pasted several times, is one file.
This module knows nothing about notes; which images are still linked is
decided by the caller.
"""

import hashlib
from pathlib import Path

from plainpad.atomic_file import write_bytes_atomically
from plainpad.config import (
    IMAGE_HASH_LENGTH,
    IMAGE_MAX_BYTES,
    IMAGE_SIGNATURES,
)


class ImageFormatError(ValueError):
    """Some bytes are not a PNG, JPEG, GIF, or WebP, or are too large."""


def image_extension(data: bytes) -> str:
    """Return the extension for image bytes, judged by how they start.

    Raises ImageFormatError for anything that is not an accepted format.
    """
    for offset, signature, extension in IMAGE_SIGNATURES:
        if data[offset:offset + len(signature)] == signature:
            return extension
    raise ImageFormatError("Not a PNG, JPEG, GIF, or WebP image.")


class ImageStore:
    """All image files in one folder, plus their trash folder."""

    def __init__(self, images_dir: Path, trash_dir: Path) -> None:
        """Remember both folders and create the images folder.

        The trash folder is only created when something is moved there.
        """
        self._images_dir = images_dir
        self._trash_dir = trash_dir
        images_dir.mkdir(parents=True, exist_ok=True)

    @property
    def folder(self) -> Path:
        """The folder that holds the image files."""
        return self._images_dir

    def add(self, data: bytes) -> str:
        """Keep a copy of an image and return its file name.

        The bytes are stored exactly as given, which is what keeps an
        animated GIF animated. Adding the same image again returns the
        same name without writing. Raises ImageFormatError if the bytes
        are not an accepted image or exceed config.IMAGE_MAX_BYTES.
        """
        if len(data) > IMAGE_MAX_BYTES:
            raise ImageFormatError("The image is too large.")
        digest = hashlib.sha256(data).hexdigest()[:IMAGE_HASH_LENGTH]
        name = f"{digest}{image_extension(data)}"
        if not self.path_of(name).exists():
            write_bytes_atomically(self.path_of(name), data)
        return name

    def read(self, name: str) -> bytes:
        """Return the bytes of a stored image."""
        return self.path_of(name).read_bytes()

    def exists(self, name: str) -> bool:
        """Return True if an image file has this name."""
        return self.path_of(name).is_file()

    def names(self) -> list[str]:
        """Return the file name of every stored image, sorted."""
        return sorted(
            path.name
            for path in self._images_dir.iterdir()
            if path.is_file()
        )

    def trash_unused(self, referenced: set[str]) -> int:
        """Move every image not in ``referenced`` to the trash folder.

        Returns how many were moved. Names are compared without regard to
        case, as Windows does. A trashed file with the same name holds
        the same picture, since the name is its hash, so replacing it
        loses nothing.
        """
        kept = {name.casefold() for name in referenced}
        unused = [
            name for name in self.names() if name.casefold() not in kept
        ]
        if unused:
            self._trash_dir.mkdir(parents=True, exist_ok=True)
        for name in unused:
            self.path_of(name).replace(self._trash_dir / name)
        return len(unused)

    def path_of(self, name: str) -> Path:
        """Return the file path for an image name."""
        return self._images_dir / name
