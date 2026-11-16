"""The Settings tab: an editor for the CSS used by the View tab."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from plainpad.autosave import AutosaveTimer
from plainpad.config import AUTOSAVE_DELAY_MS
from plainpad.gui.dialogs import confirm

READ_ONLY_HINT = (
    "The Default theme cannot be edited, so it is always there to fall "
    "back to. Pick another theme under Settings > Theme to change its CSS."
)


class SettingsTab(QWidget):
    """A CSS editor with a "Reset to default" button.

    Shows the CSS of the current theme. Autosaves on the same idle rule
    as notes. Read-only for a theme that cannot be edited.
    """

    # Time to write the CSS to disk: full CSS text.
    save_due = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty editor, the reset button, and the
        AutosaveTimer. Call ``load_css`` to fill it."""
        super().__init__(parent)
        self._default_css = ""
        self._save_failed = False
        self._editor = QPlainTextEdit(self)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._autosave = AutosaveTimer(AUTOSAVE_DELAY_MS, self)
        self._autosave.due.connect(self.emit_save)
        self._editor.textChanged.connect(self.on_text_changed)

        self._hint = QLabel(READ_ONLY_HINT, self)
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        self._reset_button = QPushButton("Reset to default", self)
        self._reset_button.clicked.connect(self.reset_to_default)
        button_row = QHBoxLayout()
        button_row.addWidget(self._hint, 1)
        button_row.addWidget(self._reset_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self._editor)
        layout.addLayout(button_row)

    def load_css(self, css: str, default_css: str, editable: bool) -> None:
        """Show another theme's CSS. Flush pending saves first.

        Loading starts a fresh undo history, since undoing into another
        theme's CSS would make no sense.
        """
        self._save_failed = False
        self._default_css = default_css
        self._editor.setPlainText(css)
        # setPlainText fires textChanged while the document still counts
        # as modified, which starts a save of text nobody typed.
        self._autosave.cancel()
        self._editor.setReadOnly(not editable)
        self._reset_button.setEnabled(editable)
        self._hint.setVisible(not editable)

    def current_css(self) -> str:
        """Return the CSS as it is in the editor now."""
        return self._editor.toPlainText()

    def flush(self) -> None:
        """Emit ``save_due`` now if there are unsaved edits or the last
        save failed."""
        if self._autosave.is_pending():
            self._autosave.flush()
        elif self._save_failed:
            self.emit_save()

    def save_failed(self) -> None:
        """Remember that the last save failed so the next flush retries."""
        self._save_failed = True

    def has_unsaved_changes(self) -> bool:
        """Return True if the CSS has edits not yet on disk."""
        return self._save_failed or self._autosave.is_pending()

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
        self._save_failed = False
        self._editor.document().setModified(False)
        self.save_due.emit(self.current_css())
