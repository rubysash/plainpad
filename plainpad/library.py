"""The single entry point the GUI uses for notes and categories.

Library keeps NoteStore and CategoryIndex consistent with each other. For
example, renaming a note must rename the file and carry its category over.
The GUI never touches NoteStore or CategoryIndex directly.
"""

from pathlib import Path

from plainpad.categories import CategoryIndex, CategoryNameError
from plainpad.config import (
    IMAGES_DIR_NAME,
    INDEX_FILE_NAME,
    NOTES_DIR_NAME,
    TRASH_DIR_NAME,
    UNCATEGORIZED_ID,
)
from plainpad.crud import NoteNameError, NoteStore
from plainpad.image_links import image_link_for, image_names_in
from plainpad.image_sources import ImageSourceError, ImageSourceReader
from plainpad.images import ImageFormatError, ImageStore
from plainpad.models import Category, CategoryListing, ImportedText
from plainpad.render import MarkdownRenderer
from plainpad.rich_export import RichTextExporter
from plainpad.rich_import import RichTextImporter
from plainpad.search import find_matching_notes

# Re-exported so the GUI can catch them without importing layer 1.
__all__ = [
    "Library",
    "NoteNameError",
    "CategoryNameError",
    "ImageFormatError",
    "ImageSourceError",
]


class Library:
    """Notes, categories, images, and search behind one interface."""

    def __init__(
        self, data_dir: Path, sources: ImageSourceReader | None = None
    ) -> None:
        """Open the data folder, creating it and its contents if needed.

        Builds the NoteStore, ImageStore, and CategoryIndex, then
        reconciles the index with the note files actually present.
        ``sources`` fetches pasted images; tests pass one that stays off
        the network.
        """
        trash_dir = data_dir / TRASH_DIR_NAME
        self._notes = NoteStore(data_dir / NOTES_DIR_NAME, trash_dir)
        self._images = ImageStore(
            data_dir / IMAGES_DIR_NAME, trash_dir / IMAGES_DIR_NAME
        )
        self._sources = sources or ImageSourceReader()
        self._importer = RichTextImporter(self._images, self._sources)
        self._exporter = RichTextExporter(MarkdownRenderer(), self._images)
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

    # --- Images ----------------------------------------------------------

    def images_folder(self) -> Path:
        """Return the folder that holds every image file."""
        return self._images.folder

    def add_image(self, data: bytes) -> str:
        """Store image bytes and return the markdown link that shows them.

        Raises ImageFormatError if the bytes are not an accepted image.
        """
        return image_link_for(self._images.add(data))

    def add_image_from(self, address: str) -> str:
        """Store the image at a web, file, or data address; return its link.

        Raises ImageSourceError if the address cannot be read and
        ImageFormatError if what it holds is not an accepted image.
        """
        return self.add_image(self._sources.read(address))

    def clean_up_unused_images(self) -> int:
        """Move images that no note links to into the trash.

        Trashed notes count as linking, so restoring one by hand never
        finds its pictures gone. Returns how many images were moved.
        """
        referenced: set[str] = set()
        for text in self._notes.texts_including_trash():
            referenced |= image_names_in(text)
        return self._images.trash_unused(referenced)

    # --- Rich copy and paste ---------------------------------------------

    def import_rich_text(self, html: str) -> ImportedText:
        """Convert clipboard HTML to markdown, storing its images."""
        return self._importer.markdown_from(html)

    def rich_html_of_note(self, markdown_text: str) -> str:
        """Return a note as HTML with images embedded, for the clipboard."""
        return self._exporter.note_html(markdown_text)

    def rich_html_of_selection(self, copied_html: str) -> str:
        """Return the View tab's copied HTML, theme off, images embedded."""
        return self._exporter.selection_html(copied_html)

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
