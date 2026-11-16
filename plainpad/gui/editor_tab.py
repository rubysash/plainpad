"""The Edit tab: a markdown editor with autosave and per-note undo.

Each note opened during a session gets its own QTextDocument. Swapping the
document, instead of replacing the text, is what keeps every note's undo
history intact when the user moves between notes.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QPlainTextDocumentLayout, QPlainTextEdit, QWidget

from plainpad.autosave import AutosaveTimer
from plainpad.config import AUTOSAVE_DELAY_MS

NO_NOTE_HINT = "Select a note, or press Ctrl+N to create one."


class EditorTab(QPlainTextEdit):
    """Plain text editor for the open note."""

    # Time to write the note to disk: note name, full text.
    save_due = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create a disabled, word-wrapped editor and its AutosaveTimer."""
        super().__init__(parent)
        # QPlainTextEdit deletes a replaced document if the editor is its
        # parent, so the per-note documents belong to a separate owner.
        self._document_owner = QObject(self)
        self._documents: dict[str, QTextDocument] = {}
        # Notes whose last save failed; their text lives on in _documents.
        self._failed: set[str] = set()
        self._current_name: str | None = None
        self._blank = self.new_document("")
        self._autosave = AutosaveTimer(AUTOSAVE_DELAY_MS, self)
        self._autosave.due.connect(self.emit_save)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.textChanged.connect(self.on_text_changed)
        self.close_note()

    def new_document(self, text: str) -> QTextDocument:
        """Create an unmodified plain text document holding ``text``."""
        document = QTextDocument(self._document_owner)
        # Without this layout QPlainTextEdit shows nothing.
        document.setDocumentLayout(QPlainTextDocumentLayout(document))
        document.setPlainText(text)
        document.setModified(False)
        return document

    def open_note(self, name: str, text: str) -> None:
        """Show a note.

        Reuses the note's existing document if it was opened earlier in
        this session; otherwise creates one from ``text``. ``text`` is
        ignored when a document already exists, because that document may
        hold newer edits and owns the undo history.
        """
        if name == self._current_name:
            return
        self.flush()
        document = self._documents.get(name)
        if document is None:
            document = self.new_document(text)
            self._documents[name] = document
        document.setDefaultFont(self.font())
        self._current_name = name
        self.setDocument(document)
        self.setPlaceholderText("")
        self.setEnabled(True)

    def close_note(self) -> None:
        """Show no note and disable the editor."""
        self.flush()
        self._current_name = None
        self.setDocument(self._blank)
        self.setPlaceholderText(NO_NOTE_HINT)
        self.setEnabled(False)

    def current_note_name(self) -> str | None:
        """Return the name of the open note, or None."""
        return self._current_name

    def current_text(self) -> str:
        """Return the open note's text as it is in the editor now."""
        return self.toPlainText()

    def flush(self) -> None:
        """Emit ``save_due`` now for unsaved edits and failed saves.

        Every note whose earlier save failed is retried, not only the
        open one, because switching notes must not abandon its text.
        """
        retry, self._failed = self._failed, set()
        if self._autosave.is_pending():
            # Flushing the timer saves the open note; do not save it twice.
            retry.discard(self._current_name)
            self._autosave.flush()
        for name in retry:
            document = self._documents.get(name)
            if document is not None:
                self.save_due.emit(name, document.toPlainText())

    def save_failed(self, name: str) -> None:
        """Remember that a note's save failed so the next flush retries."""
        if name in self._documents:
            self._failed.add(name)

    def has_unsaved_changes(self) -> bool:
        """Return True if any note has edits not yet on disk."""
        return bool(self._failed) or self._autosave.is_pending()

    def note_was_renamed(self, old_name: str, new_name: str) -> None:
        """Keep the note's document and undo history under its new name."""
        document = self._documents.pop(old_name, None)
        if document is not None:
            self._documents[new_name] = document
        if old_name in self._failed:
            self._failed.discard(old_name)
            self._failed.add(new_name)
        if self._current_name == old_name:
            self._current_name = new_name

    def note_was_deleted(self, name: str) -> None:
        """Discard the note's document; close it if it is the open note."""
        if self._current_name == name:
            # Cancel first so closing does not write the note back.
            self._autosave.cancel()
            self.close_note()
        self._failed.discard(name)
        document = self._documents.pop(name, None)
        if document is not None:
            document.deleteLater()

    def on_text_changed(self) -> None:
        """Restart the autosave countdown after a real edit.

        Loading or swapping a document also fires textChanged; the
        modified flag tells those apart from typing.
        """
        if self._current_name is not None and self.document().isModified():
            self._autosave.restart()

    def emit_save(self) -> None:
        """Announce the open note's text and mark it as saved.

        Clearing the modified flag moves the document's clean point, so
        undoing back past a save counts as an edit and is saved too.
        """
        if self._current_name is None:
            return
        # This save supersedes any earlier failed one; a new failure
        # re-adds the note through save_failed.
        self._failed.discard(self._current_name)
        self.document().setModified(False)
        self.save_due.emit(self._current_name, self.toPlainText())
