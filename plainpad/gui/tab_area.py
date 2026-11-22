"""The right side of the window: the Edit and View tabs."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtWidgets import QTabWidget, QWidget

from plainpad.gui.editor_tab import EditorTab
from plainpad.gui.preview_tab import PreviewTab
from plainpad.render import MarkdownRenderer


class TabArea(QTabWidget):
    """Holds the two tabs and keeps them consistent when switching.

    Changing tabs flushes pending saves, and showing the View tab renders
    the note currently in the editor.
    """

    def __init__(
        self,
        renderer: MarkdownRenderer,
        view_css: Callable[[], str],
        notes_folder: Path,
        parent: QWidget | None = None,
    ) -> None:
        """Create the Edit and View tabs.

        ``view_css`` returns the CSS for the View tab. It is asked on
        every render, so hand edits to a theme's CSS show up at once.
        ``notes_folder`` lets the View tab find the images notes link.
        """
        super().__init__(parent)
        self._view_css = view_css
        self._editor = EditorTab(self)
        self._preview = PreviewTab(renderer, notes_folder, self)
        self._edit_index = self.addTab(self._editor, "Edit")
        self._view_index = self.addTab(self._preview, "View")
        self.currentChanged.connect(self.on_tab_changed)

    @property
    def editor(self) -> EditorTab:
        """The note editor, for MainWindow to connect to."""
        return self._editor

    @property
    def preview(self) -> PreviewTab:
        """The rendered view, for MainWindow to connect to."""
        return self._preview

    def show_edit_tab(self) -> None:
        """Switch to the Edit tab."""
        self.setCurrentIndex(self._edit_index)

    def show_view_tab(self) -> None:
        """Switch to the View tab."""
        self.setCurrentIndex(self._view_index)

    def toggle_edit_and_view(self) -> None:
        """Switch between the Edit and View tabs."""
        if self.currentIndex() == self._edit_index:
            self.show_view_tab()
        else:
            self.show_edit_tab()

    def flush_pending_saves(self) -> None:
        """Save the open note now if it has unsaved edits."""
        self._editor.flush()

    def has_unsaved_changes(self) -> bool:
        """Return True if a note has edits not yet on disk."""
        return self._editor.has_unsaved_changes()

    def on_tab_changed(self, index: int) -> None:
        """Flush pending saves; render the note if View was selected."""
        self.flush_pending_saves()
        self.refresh_view()

    def refresh_view(self) -> None:
        """Re-render the open note if the View tab is showing."""
        if self.currentIndex() != self._view_index:
            return
        if self._editor.current_note_name() is None:
            self._preview.show_nothing()
            return
        self._preview.show_markdown(
            self._editor.current_text(), self._view_css()
        )
