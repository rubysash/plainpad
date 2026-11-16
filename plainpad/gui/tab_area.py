"""The right side of the window: the Edit, View, and Settings tabs."""

from PyQt6.QtWidgets import QTabWidget, QWidget

from plainpad.gui.editor_tab import EditorTab
from plainpad.gui.preview_tab import PreviewTab
from plainpad.gui.settings_tab import SettingsTab
from plainpad.render import MarkdownRenderer


class TabArea(QTabWidget):
    """Holds the three tabs and keeps them consistent when switching.

    Changing tabs flushes pending saves, and showing the View tab renders
    the note currently in the editor with the CSS currently in Settings.
    """

    def __init__(
        self, renderer: MarkdownRenderer, parent: QWidget | None = None
    ) -> None:
        """Create the three tabs in Edit, View, Settings order."""
        super().__init__(parent)
        self._editor = EditorTab(self)
        self._preview = PreviewTab(renderer, self)
        self._settings = SettingsTab(self)
        self._edit_index = self.addTab(self._editor, "Edit")
        self._view_index = self.addTab(self._preview, "View")
        self._settings_index = self.addTab(self._settings, "Settings")
        self.currentChanged.connect(self.on_tab_changed)

    @property
    def editor(self) -> EditorTab:
        """The note editor, for MainWindow to connect to."""
        return self._editor

    @property
    def preview(self) -> PreviewTab:
        """The rendered view, for MainWindow to connect to."""
        return self._preview

    @property
    def settings(self) -> SettingsTab:
        """The CSS editor, for MainWindow to connect to."""
        return self._settings

    def show_edit_tab(self) -> None:
        """Switch to the Edit tab."""
        self.setCurrentIndex(self._edit_index)

    def show_view_tab(self) -> None:
        """Switch to the View tab."""
        self.setCurrentIndex(self._view_index)

    def show_settings_tab(self) -> None:
        """Switch to the Settings tab."""
        self.setCurrentIndex(self._settings_index)

    def toggle_edit_and_view(self) -> None:
        """Switch between the Edit and View tabs."""
        if self.currentIndex() == self._edit_index:
            self.show_view_tab()
        else:
            self.show_edit_tab()

    def flush_pending_saves(self) -> None:
        """Save the open note and the CSS now if either has unsaved edits."""
        self._editor.flush()
        self._settings.flush()

    def has_unsaved_changes(self) -> bool:
        """Return True if a note or the CSS has edits not yet on disk."""
        return (
            self._editor.has_unsaved_changes()
            or self._settings.has_unsaved_changes()
        )

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
            self._editor.current_text(), self._settings.current_css()
        )
