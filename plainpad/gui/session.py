"""What the window remembers between runs, stored with QSettings."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMainWindow, QSplitter

from plainpad.config import (
    DEFAULT_SPLITTER_SIZES,
    DEFAULT_WINDOW_SIZE,
    SETTINGS_GEOMETRY_KEY,
    SETTINGS_LAST_NOTE_KEY,
    SETTINGS_SPLITTER_KEY,
    SETTINGS_THEME_KEY,
)


class SessionMemory:
    """Window size, splitter position, and the last open note.

    QSettings finds its storage from the organization and application
    names set on the QApplication.
    """

    def __init__(self) -> None:
        """Open the application's settings store."""
        self._settings = QSettings()

    def restore_layout(self, window: QMainWindow, splitter: QSplitter) -> None:
        """Apply the remembered window geometry and splitter position."""
        geometry = self._settings.value(SETTINGS_GEOMETRY_KEY)
        if geometry is None or not window.restoreGeometry(geometry):
            window.resize(*DEFAULT_WINDOW_SIZE)
        state = self._settings.value(SETTINGS_SPLITTER_KEY)
        if state is None or not splitter.restoreState(state):
            splitter.setSizes(list(DEFAULT_SPLITTER_SIZES))

    def last_note(self) -> str | None:
        """Return the name of the note open at the last exit, or None."""
        name = self._settings.value(SETTINGS_LAST_NOTE_KEY, "", type=str)
        return name or None

    def theme(self) -> str | None:
        """Return the name of the theme chosen last, or None."""
        name = self._settings.value(SETTINGS_THEME_KEY, "", type=str)
        return name or None

    def save_theme(self, name: str) -> None:
        """Remember the chosen theme for the next run."""
        self._settings.setValue(SETTINGS_THEME_KEY, name)

    def save(
        self,
        window: QMainWindow,
        splitter: QSplitter,
        note_name: str | None,
    ) -> None:
        """Remember the layout and the open note for the next run."""
        self._settings.setValue(SETTINGS_GEOMETRY_KEY, window.saveGeometry())
        self._settings.setValue(SETTINGS_SPLITTER_KEY, splitter.saveState())
        self._settings.setValue(SETTINGS_LAST_NOTE_KEY, note_name or "")
