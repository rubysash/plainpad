"""The category index: which categories exist and which note is in which.

The index is one JSON file. It stores user-defined categories and a mapping
from note name to category id. The built-in Uncategorized category is never
stored; a note without a mapping belongs to it.
"""

import json
import secrets
from pathlib import Path

from plainpad.atomic_file import write_text_atomically
from plainpad.config import (
    CATEGORY_ID_BYTES,
    CORRUPT_INDEX_SUFFIX,
    INDEX_JSON_INDENT,
    INDEX_VERSION,
    TEXT_ENCODING,
    UNCATEGORIZED_ID,
    UNCATEGORIZED_NAME,
)
from plainpad.crud import timestamp_name
from plainpad.models import Category


class CategoryNameError(ValueError):
    """A category name is empty or already in use."""


class CategoryIndex:
    """In-memory copy of index.json. Every change is saved immediately."""

    def __init__(self, index_file: Path) -> None:
        """Load the index, or start empty if the file does not exist.

        An unreadable index is renamed aside, not overwritten, so the
        user can recover it by hand; the app then starts with no
        categories.
        """
        self._file = index_file
        self._names: dict[str, str] = {}
        self._assignments: dict[str, str] = {}
        try:
            data = json.loads(index_file.read_text(encoding=TEXT_ENCODING))
            names = {c["id"]: c["name"] for c in data["categories"]}
            assignments = dict(data["assignments"])
        except FileNotFoundError:
            return
        except (ValueError, KeyError, TypeError, AttributeError):
            backup = f"{index_file.name}.{timestamp_name()}"
            index_file.rename(
                index_file.with_name(backup + CORRUPT_INDEX_SUFFIX)
            )
            return
        self._names = names
        self._assignments = assignments

    def categories(self) -> list[Category]:
        """Return user categories sorted by name, then Uncategorized."""
        ordered = sorted(
            self._names.items(), key=lambda pair: pair[1].casefold()
        )
        listed = [Category(cid, name) for cid, name in ordered]
        return listed + [Category(UNCATEGORIZED_ID, UNCATEGORIZED_NAME)]

    def add(self, name: str) -> Category:
        """Create a category with a new random id and return it.

        Raises CategoryNameError if the name is empty or taken.
        """
        name = self._checked_name(name)
        category_id = secrets.token_hex(CATEGORY_ID_BYTES)
        while category_id in self._names or category_id == UNCATEGORIZED_ID:
            category_id = secrets.token_hex(CATEGORY_ID_BYTES)
        self._names[category_id] = name
        self.save()
        return Category(category_id, name)

    def rename(self, category_id: str, new_name: str) -> None:
        """Change a category's display name. Its id and notes are kept.

        Raises CategoryNameError if the name is empty or taken, or if the
        category is Uncategorized.
        """
        if category_id == UNCATEGORIZED_ID:
            raise CategoryNameError(
                f"{UNCATEGORIZED_NAME} cannot be renamed."
            )
        if category_id not in self._names:
            raise KeyError(category_id)
        self._names[category_id] = self._checked_name(new_name, category_id)
        self.save()

    def remove(self, category_id: str) -> None:
        """Delete a category. Its notes fall back to Uncategorized.

        Raises CategoryNameError for Uncategorized.
        """
        if category_id == UNCATEGORIZED_ID:
            raise CategoryNameError(
                f"{UNCATEGORIZED_NAME} cannot be deleted."
            )
        self._names.pop(category_id, None)
        self._assignments = {
            note: cid
            for note, cid in self._assignments.items()
            if cid != category_id
        }
        self.save()

    def category_of(self, note_name: str) -> str:
        """Return the id of the category a note is in."""
        return self._assignments.get(note_name, UNCATEGORIZED_ID)

    def assign(self, note_name: str, category_id: str) -> None:
        """Put a note into a category, replacing its previous one."""
        if category_id == UNCATEGORIZED_ID:
            self._assignments.pop(note_name, None)
        elif category_id in self._names:
            self._assignments[note_name] = category_id
        else:
            raise KeyError(category_id)
        self.save()

    def rename_note(self, old_name: str, new_name: str) -> None:
        """Carry a note's category over to its new name."""
        if old_name in self._assignments:
            self._assignments[new_name] = self._assignments.pop(old_name)
            self.save()

    def forget_note(self, note_name: str) -> None:
        """Drop a note's mapping, for use when the note is deleted."""
        if self._assignments.pop(note_name, None) is not None:
            self.save()

    def reconcile(self, existing_note_names: list[str]) -> None:
        """Drop mappings for missing notes or unknown categories."""
        existing = set(existing_note_names)
        kept = {
            note: cid
            for note, cid in self._assignments.items()
            if note in existing and cid in self._names
        }
        if kept != self._assignments:
            self._assignments = kept
            self.save()

    def save(self) -> None:
        """Write the index to disk atomically."""
        data = {
            "version": INDEX_VERSION,
            "categories": [
                {"id": cid, "name": name} for cid, name in self._names.items()
            ],
            "assignments": self._assignments,
        }
        text = json.dumps(data, indent=INDEX_JSON_INDENT, ensure_ascii=False)
        write_text_atomically(self._file, text + "\n")

    def _checked_name(self, name: str, renaming: str | None = None) -> str:
        """Return the trimmed name, or raise CategoryNameError.

        ``renaming`` is the id of the category being renamed, so changing
        only the case of its own name is allowed.
        """
        name = name.strip()
        if not name:
            raise CategoryNameError("A category name cannot be empty.")
        taken = {
            other.casefold()
            for cid, other in self._names.items()
            if cid != renaming
        }
        taken.add(UNCATEGORIZED_NAME.casefold())
        if name.casefold() in taken:
            raise CategoryNameError(f"A category named '{name}' exists.")
        return name
