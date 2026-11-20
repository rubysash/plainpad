"""The single entry point the GUI uses for notes and categories.

Library keeps NoteStore and CategoryIndex consistent with each other. For
example, renaming a note must rename the file and carry its category over.
The GUI never touches NoteStore or CategoryIndex directly.
"""

from pathlib import Path

from plainpad.categories import CategoryIndex, CategoryNameError
from plainpad.config import (
    INDEX_FILE_NAME,
    NOTES_DIR_NAME,
    TRASH_DIR_NAME,
    UNCATEGORIZED_ID,
)
from plainpad.crud import NoteNameError, NoteStore
from plainpad.models import Category, CategoryListing
from plainpad.search import find_matching_notes

# Re-exported so the GUI can catch them without importing layer 1.
__all__ = ["Library", "NoteNameError", "CategoryNameError"]


class Library:
    """Notes, categories, and search behind one interface."""

    def __init__(self, data_dir: Path) -> None:
        """Open the data folder, creating it and its contents if needed.

        Builds the NoteStore and CategoryIndex, then reconciles the index
        with the note files actually present.
        """
        self._notes = NoteStore(
            data_dir / NOTES_DIR_NAME, data_dir / TRASH_DIR_NAME
        )
        self._index = CategoryIndex(data_dir / INDEX_FILE_NAME)
        self._index.reconcile(self._notes.names())

    # --- Reading ---------------------------------------------------------

    def listings(self) -> list[CategoryListing]:
        """Return every category with its notes, in display order."""
        listings = {
            category.category_id: CategoryListing(category)
            for category in self._index.categories()
        }
        fallback = listings[UNCATEGORIZED_ID]
        for name in self._notes.names():
            category_id = self._index.category_of(name)
            listings.get(category_id, fallback).note_names.append(name)
        return list(listings.values())

    def read_note(self, name: str) -> str:
        """Return a note's markdown text."""
        return self._notes.read(name)

    def note_exists(self, name: str) -> bool:
        """Return True if a note with this name exists."""
        return self._notes.exists(name)

    def note_path(self, name: str) -> Path:
        """Return the file a note is stored in."""
        return self._notes.path_of(name)

    def notes_folder(self) -> Path:
        """Return the folder that holds every note file."""
        return self._notes.folder

    def search(self, query: str) -> set[str]:
        """Return the names of notes matching a keyword."""
        return find_matching_notes(self._notes, query)

    # --- Notes -----------------------------------------------------------

    def create_note(self, category_id: str) -> str:
        """Create an empty timestamp-named note in a category.

        Returns the new note's name.
        """
        name = self._notes.create()
        self._index.assign(name, category_id)
        return name

    def save_note(self, name: str, text: str) -> None:
        """Write a note's text to disk."""
        self._notes.write(name, text)

    def rename_note(self, old_name: str, new_name: str) -> None:
        """Rename a note and keep it in the same category.

        Raises NoteNameError if the new name is not allowed.
        """
        self._notes.rename(old_name, new_name)
        self._index.rename_note(old_name, new_name)

    def delete_note(self, name: str) -> None:
        """Move a note to the trash and remove it from its category."""
        self._notes.delete(name)
        self._index.forget_note(name)

    def move_note(self, name: str, category_id: str) -> None:
        """File a note under a different category."""
        self._index.assign(name, category_id)

    # --- Categories ------------------------------------------------------

    def create_category(self, name: str) -> Category:
        """Create a category. Raises CategoryNameError on a bad name."""
        return self._index.add(name)

    def rename_category(self, category_id: str, new_name: str) -> None:
        """Rename a category. Raises CategoryNameError on a bad name."""
        self._index.rename(category_id, new_name)

    def delete_category(self, category_id: str) -> None:
        """Delete a category; its notes move to Uncategorized."""
        self._index.remove(category_id)
