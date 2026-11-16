"""The Settings tab: an editor for the CSS used by the View tab."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from plainpad.autosave import AutosaveTimer
from plainpad.config import AUTOSAVE_DELAY_MS
from plainpad.gui.dialogs import confirm


class SettingsTab(QWidget):
    """A CSS editor with a "Reset to default" button.

    Autosaves on the same idle rule as notes.
    """

    # Time to write the CSS to disk: full CSS text.
    save_due = pyqtSignal(str)

    def __init__(
        self, css: str, default_css: str, parent: QWidget | None = None
    ) -> None:
        """Create the editor filled with ``css``, the reset button, and
        the AutosaveTimer."""
        super().__init__(parent)
        self._default_css = default_css
        self._editor = QPlainTextEdit(self)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.setPlainText(css)
        self._autosave = AutosaveTimer(AUTOSAVE_DELAY_MS, self)
        self._autosave.due.connect(self.emit_save)
        self._editor.textChanged.connect(self.on_text_changed)

        reset_button = QPushButton("Reset to default", self)
        reset_button.clicked.connect(self.reset_to_default)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(reset_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self._editor)
        layout.addLayout(button_row)

    def current_css(self) -> str:
        """Return the CSS as it is in the editor now."""
        return self._editor.toPlainText()

    def flush(self) -> None:
        """Emit ``save_due`` immediately if there are unsaved edits."""
        self._autosave.flush()

    def reset_to_default(self) -> None:
        """After confirmation, replace the CSS with the shipped default.

        The replacement is one undoable edit, so Ctrl+Z brings the user's
        CSS back.
        """
        if not confirm(
            self, "Reset CSS", "Replace your CSS with the default CSS?"
        ):
            return
        cursor = QTextCursor(self._editor.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(self._default_css)
        cursor.endEditBlock()

    def on_text_changed(self) -> None:
        """Restart the autosave countdown after a real edit."""
        if self._editor.document().isModified():
            self._autosave.restart()

    def emit_save(self) -> None:
        """Announce the CSS and mark it as saved.

        Clearing the modified flag moves the clean point, so undoing back
        past a save counts as an edit and is saved too.
        """
        self._editor.document().setModified(False)
        self.save_due.emit(self.current_css())
