"""Crash-safe file writing, shared by notes, the index, and the CSS."""

import os
import tempfile
from pathlib import Path

from plainpad.config import ATOMIC_TEMP_SUFFIX, TEXT_ENCODING


def write_text_atomically(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` so the file is never left half written.

    The text goes to a temporary file in the same folder, is flushed to
    disk, and then replaces ``path`` in one step with os.replace. The
    temporary file is removed if anything fails. Missing parent folders
    are created. Line endings are written exactly as given.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=ATOMIC_TEMP_SUFFIX
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(
            descriptor, "w", encoding=TEXT_ENCODING, newline=""
        ) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
