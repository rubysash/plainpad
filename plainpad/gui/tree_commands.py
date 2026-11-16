"""Note and category changes started from the menu or the tree.

TreeCommands is the half of the window's wiring that creates, renames,
moves, and deletes things. It asks the user when needed, calls Library,
and tells the editor what changed. It reports back through signals that
MainWindow connects.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from plainpad.config import UNCATEGORIZED_ID, UNCATEGORIZED_NAME
from plainpad.gui.dialogs import ask_for_name, confirm
from plainpad.gui.editor_tab import EditorTab
from plainpad.gui.note_tree import NoteTree
from plainpad.library import CategoryNameError, Library, NoteNameError


class TreeCommands(QObject):
    """Acts on the selected tree row through the Library."""

    # The stored notes or categories changed; the tree must be rebuilt.
    tree_changed = pyqtSignal()
    # A new note exists and should be opened: note name.
    note_created = pyqtSignal(str)
    # A message for the status bar.
    status_message = pyqtSignal(str)

    def __init__(
        self,
        library: Library,
        tree: NoteTree,
        editor: EditorTab,
        window: QWidget,
    ) -> None:
        """Remember the collaborators; ``window`` parents the dialogs."""
        super().__init__(window)
        self._library = library
        self._tree = tree
        self._editor = editor
        self._window = window

    def create_note(self) -> None:
        """Create a note in the selected category, or Uncategorized."""
        category_id = self._tree.selected_category_id() or UNCATEGORIZED_ID
        try:
            name = self._library.create_note(category_id)
        except OSError as error:
            self.status_message.emit(f"Could not create a note: {error}")
            return
        self.note_created.emit(name)

    def create_category(self) -> None:
        """Ask for a name and create the category."""
        name = ask_for_name(self._window, "New Category", "Category name:")
        if name is None:
            return
        try:
            self._library.create_category(name)
        except (CategoryNameError, OSError) as error:
            self.status_message.emit(f"Could not create category: {error}")
            return
        self.tree_changed.emit()

    def move_note(self, name: str, category_id: str) -> None:
        """Refile a note after a drop."""
        try:
            self._library.move_note(name, category_id)
        except OSError as error:
            self.status_message.emit(f"Could not move {name}: {error}")
            return
        self.tree_changed.emit()
        self._tree.select_note(name)

    def rename_selected(self) -> None:
        """Start in-place rename of the selected note or category."""
        self._editor.flush()
        self._tree.edit_selected()

    def apply_note_rename(self, old_name: str, new_name: str) -> None:
        """Rename a note after the tree edit is committed.

        On a bad name the tree is rebuilt, which puts the old name back,
        and the reason is shown in the status bar.
        """
        if new_name == old_name:
            return
        self._editor.flush()
        try:
            self._library.rename_note(old_name, new_name)
        except (NoteNameError, OSError) as error:
            self.status_message.emit(f"Rename failed: {error}")
            self.tree_changed.emit()
            return
        self._editor.note_was_renamed(old_name, new_name)
        self.tree_changed.emit()
        self._tree.select_note(new_name)

    def apply_category_rename(self, category_id: str, new_name: str) -> None:
        """Rename a category after the tree edit is committed."""
        try:
            self._library.rename_category(category_id, new_name)
        except (CategoryNameError, OSError) as error:
            self.status_message.emit(f"Rename failed: {error}")
        self.tree_changed.emit()

    def delete_selected(self) -> None:
        """Delete the selected note or category, after confirmation."""
        label = self._tree.selected_label()
        if self._tree.category_is_selected():
            self.delete_category(self._tree.selected_category_id(), label)
            return
        name = self._tree.selected_note_name()
        if name is not None:
            self.delete_note(name)

    def delete_note(self, name: str) -> None:
        """Move a note to the trash, after confirmation."""
        question = f"Move '{name}' to the trash?"
        if not confirm(self._window, "Delete Note", question):
            return
        # Flush first so the trashed file holds the latest text.
        self._editor.flush()
        try:
            self._library.delete_note(name)
        except OSError as error:
            self.status_message.emit(f"Could not delete {name}: {error}")
            return
        self._editor.note_was_deleted(name)
        self.tree_changed.emit()

    def delete_category(self, category_id: str, name: str) -> None:
        """Delete a category after confirmation; its notes are kept."""
        if category_id == UNCATEGORIZED_ID:
            message = f"{UNCATEGORIZED_NAME} cannot be deleted."
            self.status_message.emit(message)
            return
        question = (
            f"Delete category '{name}'? "
            f"Its notes move to {UNCATEGORIZED_NAME}."
        )
        if not confirm(self._window, "Delete Category", question):
            return
        try:
            self._library.delete_category(category_id)
        except OSError as error:
            self.status_message.emit(f"Could not delete {name}: {error}")
            return
        self.tree_changed.emit()
