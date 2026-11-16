"""The left side of the window: a search box above the category tree."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from plainpad.config import SEARCH_DELAY_MS
from plainpad.gui.note_tree import NoteTree


class Sidebar(QWidget):
    """Search box and note tree stacked vertically.

    The search box waits config.SEARCH_DELAY_MS after the last keystroke
    before announcing a search, so the tree is not refiltered on every
    letter.
    """

    # Emitted with the trimmed search text; empty means "clear the filter".
    search_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the search box, the tree, and the search delay timer."""
        super().__init__(parent)
        self._search_box = QLineEdit(self)
        self._search_box.setPlaceholderText("search...")
        self._search_box.setClearButtonEnabled(True)
        self._tree = NoteTree(self)

        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(SEARCH_DELAY_MS)
        self._delay.timeout.connect(
            lambda: self.search_requested.emit(self.current_query())
        )
        self._search_box.textChanged.connect(self.on_text_changed)

        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self._search_box)
        escape.setContext(Qt.ShortcutContext.WidgetShortcut)
        escape.activated.connect(self.clear_search)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._search_box)
        layout.addWidget(self._tree)

    @property
    def tree(self) -> NoteTree:
        """The category tree, for MainWindow to connect to and refresh."""
        return self._tree

    def focus_search(self) -> None:
        """Move keyboard focus to the search box and select its text."""
        self._search_box.setFocus()
        self._search_box.selectAll()

    def clear_search(self) -> None:
        """Empty the search box, which clears the tree filter."""
        self._search_box.clear()

    def current_query(self) -> str:
        """Return the trimmed text currently in the search box."""
        return self._search_box.text().strip()

    def on_text_changed(self, text: str) -> None:
        """Wait for a pause in typing; clear the filter at once."""
        if text.strip():
            self._delay.start()
        else:
            self._delay.stop()
            self.search_requested.emit("")
