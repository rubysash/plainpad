"""Create, read, update, and delete note files.

A note is one UTF-8 markdown file. Its name, without the extension, is its
identity everywhere else in the application. This module knows nothing
about categories.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from plainpad.atomic_file import write_text_atomically
from plainpad.config import (
    DUPLICATE_SUFFIX_START,
    FIRST_PRINTABLE_CODE_POINT,
    FORBIDDEN_NAME_CHARACTERS,
    NOTE_EXTENSION,
    RESERVED_WINDOWS_NAMES,
    TEXT_ENCODING,
    TIMESTAMP_FORMAT,
)


class NoteNameError(ValueError):
    """A note name is empty, illegal on Windows, or already in use."""


def timestamp_name(now: datetime | None = None) -> str:
    """Return the default name for a new note, built from the local time.

    ``now`` is injectable so tests can pass a fixed time.
    """
    return (now or datetime.now()).strftime(TIMESTAMP_FORMAT)


def first_unused_name(base: str, is_taken: Callable[[str], bool]) -> str:
    """Return ``base``, or ``base-2``, ``base-3``... whichever is free."""
    candidate = base
    number = DUPLICATE_SUFFIX_START
    while is_taken(candidate):
        candidate = f"{base}-{number}"
        number += 1
    return candidate


class NoteStore:
    """All note files in one folder, plus the trash folder beside it."""

    def __init__(self, notes_dir: Path, trash_dir: Path) -> None:
        """Remember both folders and create them if they are missing."""
        self._notes_dir = notes_dir
        self._trash_dir = trash_dir
        notes_dir.mkdir(parents=True, exist_ok=True)
        trash_dir.mkdir(parents=True, exist_ok=True)

    @property
    def folder(self) -> Path:
        """The folder that holds the note files."""
        return self._notes_dir

    def names(self) -> list[str]:
        """Return every note name, sorted without regard to case."""
        found = (
            path.stem
            for path in self._notes_dir.glob(f"*{NOTE_EXTENSION}")
            if path.is_file()
        )
        return sorted(found, key=str.casefold)

    def exists(self, name: str) -> bool:
        """Return True if a note has this name, ignoring case."""
        wanted = name.casefold()
        return any(other.casefold() == wanted for other in self.names())

    def read(self, name: str) -> str:
        """Return the full text of a note."""
        return self.path_of(name).read_text(encoding=TEXT_ENCODING)

    def write(self, name: str, text: str) -> None:
        """Replace a note's text atomically.

        The text is written to a temporary file in the same folder, which
        then replaces the real file, so a crash cannot leave a partly
        written note.
        """
        write_text_atomically(self.path_of(name), text)

    def create(self, now: datetime | None = None) -> str:
        """Create an empty note with a timestamp name and return the name.

        If the timestamp name is taken, ``-2``, ``-3``, and so on is
        appended until the name is free. ``now`` is injectable for tests.
        """
        name = first_unused_name(timestamp_name(now), self.exists)
        self.write(name, "")
        return name

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a note file.

        Changing only the case of a note's own name is allowed. Raises
        NoteNameError if ``new_name`` fails validate_name.
        """
        if new_name == old_name:
            return
        self.validate_name(new_name, renaming=old_name)
        self.path_of(old_name).rename(self.path_of(new_name))

    def delete(self, name: str) -> None:
        """Move a note into the trash folder.

        If the trash already holds a file with this name, a timestamp is
        added to the trashed file's name so nothing is overwritten.
        """
        def in_trash(candidate: str) -> bool:
            return (self._trash_dir / f"{candidate}{NOTE_EXTENSION}").exists()

        trashed = name
        if in_trash(name):
            trashed = first_unused_name(f"{name}_{timestamp_name()}", in_trash)
        target = self._trash_dir / f"{trashed}{NOTE_EXTENSION}"
        self.path_of(name).rename(target)

    def validate_name(self, name: str, renaming: str | None = None) -> None:
        """Raise NoteNameError unless ``name`` may be used for a note.

        Rejects empty names, forbidden and control characters, reserved
        Windows names, and names already in use. ``renaming`` is the note
        being renamed, which does not count as a clash with itself.
        """
        if not name.strip():
            raise NoteNameError("A note name cannot be empty.")
        if any(
            character in FORBIDDEN_NAME_CHARACTERS
            or ord(character) < FIRST_PRINTABLE_CODE_POINT
            for character in name
        ):
            raise NoteNameError(
                f"A note name cannot contain {FORBIDDEN_NAME_CHARACTERS}"
                " or control characters."
            )
        # Windows reserves these names even with an extension: CON.txt.
        if name.split(".")[0].strip().upper() in RESERVED_WINDOWS_NAMES:
            raise NoteNameError(f"'{name}' is reserved by Windows.")
        same_note = renaming is not None and (
            renaming.casefold() == name.casefold()
        )
        if not same_note and self.exists(name):
            raise NoteNameError(f"A note named '{name}' already exists.")

    def path_of(self, name: str) -> Path:
        """Return the file path for a note name."""
        return self._notes_dir / f"{name}{NOTE_EXTENSION}"
