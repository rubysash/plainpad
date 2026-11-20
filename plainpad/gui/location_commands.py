"""The note tree's right-click menu: the file browser and terminals.

LocationCommands remembers which row was right-clicked and, when a menu
item is chosen, opens the OS file browser or a terminal there. Notes are
all stored in one folder, so a category row means that folder.
"""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, pyqtSignal
from PyQt6.QtWidgets import QMenu

from plainpad.desktop_launch import DesktopLauncher
from plainpad.gui.note_tree import NoteTree
from plainpad.library import Library


class LocationCommands(QObject):
    """Opens the file browser or a terminal at the right-clicked row."""

    # A message for the status bar.
    status_message = pyqtSignal(str)

    def __init__(
        self,
        library: Library,
        tree: NoteTree,
        menu: QMenu,
        launcher: DesktopLauncher,
    ) -> None:
        """Remember the collaborators; ``menu`` is shown on right-click."""
        super().__init__(tree)
        self._library = library
        self._tree = tree
        self._menu = menu
        self._launcher = launcher
        self._target = library.notes_folder()

    def show_menu(self, position: QPoint) -> None:
        """Pop up the menu for the row at a tree viewport position.

        A note row targets the note's file; anything else targets the
        notes folder. Qt selects the row under a right-click but leaves
        the old selection on empty space, so it is cleared there; that
        way New Note from empty space goes to Uncategorized, not to
        whatever was selected before.
        """
        if self._tree.itemAt(position) is None:
            self._tree.clearSelection()
        name = self._tree.note_name_at(position)
        self._target = (
            self._library.note_path(name) if name
            else self._library.notes_folder()
        )
        self._menu.popup(self._tree.viewport().mapToGlobal(position))

    def show_in_file_browser(self) -> None:
        """Show the target in the file browser, selected if it is a file."""
        self.launch(self._launcher.show_in_file_browser, "the folder")

    def open_terminal(self) -> None:
        """Open the default terminal in the target folder."""
        self.launch(self._launcher.open_terminal, "a terminal")

    def open_command_prompt(self) -> None:
        """Open Command Prompt in the target folder."""
        self.launch(self._launcher.open_command_prompt, "Command Prompt")

    def open_powershell(self) -> None:
        """Open PowerShell in the target folder."""
        self.launch(self._launcher.open_powershell, "PowerShell")

    def launch(self, open_at: Callable[[Path], None], what: str) -> None:
        """Run a launcher method on the target; report a failure."""
        try:
            open_at(self._target)
        except OSError as error:
            self.status_message.emit(f"Could not open {what}: {error}")
