"""Crash-safe file writing, shared by notes, the index, and images."""

import os
import tempfile
from pathlib import Path

from plainpad.config import ATOMIC_TEMP_SUFFIX, TEXT_ENCODING


def write_bytes_atomically(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` so the file is never left half written.

    The bytes go to a temporary file in the same folder, are flushed to
    disk, and then replace ``path`` in one step with os.replace. The
    temporary file is removed if anything fails. Missing parent folders
    are created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=ATOMIC_TEMP_SUFFIX
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def write_text_atomically(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` as UTF-8, never leaving it half written.

    Line endings are written exactly as given. See write_bytes_atomically
    for how the write is made crash-safe.
    """
    write_bytes_atomically(path, text.encode(TEXT_ENCODING))
