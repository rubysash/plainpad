"""The idle timer behind autosave.

Kept apart from the note editor so the "save after four seconds without
typing" rule lives in one small, separately readable place.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class AutosaveTimer(QObject):
    """Emits ``due`` once the user has stopped typing for a set time."""

    # Emitted when it is time to save.
    due = pyqtSignal()

    def __init__(self, delay_ms: int, parent: QObject | None = None) -> None:
        """Create a stopped single-shot timer with the given delay."""
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self.due)

    def restart(self) -> None:
        """Start the countdown again. Call this on every edit."""
        self._timer.start()

    def flush(self) -> None:
        """If a save is pending, emit ``due`` now and stop the countdown.

        Does nothing when no edit is waiting to be saved.
        """
        if self._timer.isActive():
            self._timer.stop()
            self.due.emit()

    def cancel(self) -> None:
        """Stop the countdown without saving."""
        self._timer.stop()

    def is_pending(self) -> bool:
        """Return True while an edit is waiting to be saved."""
        return self._timer.isActive()
