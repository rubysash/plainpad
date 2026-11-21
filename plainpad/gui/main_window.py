"""The main window: layout and signal wiring, no business logic.

MainWindow owns the sidebar, the tab area, the menu actions, and the
status bar. Its slots translate widget signals into Library calls and then
tell the widgets what changed. Creating, renaming, moving, and deleting
notes and categories is delegated to TreeCommands, and the tree's
right-click menu to LocationCommands. Pasting images and formatted text,
and copying a note out as rich text, is delegated to ClipboardCommands.
"""

from collections.abc import Callable
from datetime import datetime

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter

from plainpad.config import (
    APP_NAME,
    DEFAULT_THEME,
    FIRST_RUN_THEME,
    STATUS_TIME_FORMAT,
)
from plainpad.desktop_launch import DesktopLauncher
from plainpad.gui.actions import Actions, build_tree_menu, populate_menu_bar
from plainpad.gui.clipboard_commands import ClipboardCommands
from plainpad.gui.dialogs import confirm, show_about
from plainpad.gui.location_commands import LocationCommands
from plainpad.gui.session import SessionMemory
from plainpad.gui.shortcuts_dialog import ShortcutsDialog
from plainpad.gui.sidebar import Sidebar
from plainpad.gui.tab_area import TabArea
from plainpad.gui.tree_commands import TreeCommands
from plainpad.library import Library
from plainpad.render import MarkdownRenderer
from plainpad.theme import apply_theme
from plainpad.theme_store import ThemeStore


class MainWindow(QMainWindow):
    """Top-level window that connects every widget to the Library."""

    def __init__(
        self,
        library: Library,
        themes: ThemeStore,
        launcher: DesktopLauncher,
    ) -> None:
        """Build the widgets, connect them, and restore the last session."""
        super().__init__()
        self._library = library
        self._themes = themes
        self._theme = DEFAULT_THEME
        self._session = SessionMemory()
        self.build_layout()
        self._actions = Actions(
            self, themes.themes(), launcher.file_browser_label()
        )
        populate_menu_bar(self.menuBar(), self._actions)
        tree = self._sidebar.tree
        self._commands = TreeCommands(library, tree, self._tabs.editor, self)
        self._clipboard = ClipboardCommands(library, self._tabs.editor, self)
        self._locations = LocationCommands(
            library,
            tree,
            build_tree_menu(self, self._actions, launcher),
            launcher,
        )
        self.connect_actions()
        self.connect_widgets()
        self.switch_theme(self._session.theme() or FIRST_RUN_THEME)
        self.refresh_tree()
        self.restore_session()

    # --- Construction ----------------------------------------------------

    def build_layout(self) -> None:
        """Create the splitter with the sidebar left and the tabs right."""
        self._sidebar = Sidebar(self)
        self._tabs = TabArea(
            MarkdownRenderer(),
            lambda: self._themes.preview_css(self._theme),
            self._library.notes_folder(),
            self,
        )
        self._splitter = QSplitter(self)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._tabs)
        self.setCentralWidget(self._splitter)
        self.statusBar()

    def connect_actions(self) -> None:
        """Connect each menu action to the slot that carries it out."""
        actions, commands, tabs = self._actions, self._commands, self._tabs
        actions.new_note.triggered.connect(commands.create_note)
        actions.new_category.triggered.connect(commands.create_category)
        actions.rename.triggered.connect(commands.rename_selected)
        actions.delete.triggered.connect(commands.delete_selected)
        # Del only applies while the tree has focus; see Actions.
        self._sidebar.tree.addAction(actions.delete)
        actions.save_now.triggered.connect(tabs.flush_pending_saves)
        actions.clean_up_images.triggered.connect(self.clean_up_images)
        actions.exit.triggered.connect(self.close)
        edit_methods = {
            actions.undo: "undo",
            actions.redo: "redo",
            actions.cut: "cut",
            actions.copy: "copy",
            actions.paste: "paste",
            actions.select_all: "selectAll",
        }
        for action, method in edit_methods.items():
            action.triggered.connect(
                lambda _checked=False, name=method: self.edit_focused(name)
            )
        actions.copy_note_rich.triggered.connect(
            self._clipboard.copy_note_as_rich_text
        )
        actions.paste_formatted.triggered.connect(
            self._clipboard.paste_formatted
        )
        actions.find.triggered.connect(self._sidebar.focus_search)
        actions.show_edit_tab.triggered.connect(tabs.show_edit_tab)
        actions.show_view_tab.triggered.connect(tabs.show_view_tab)
        actions.toggle_edit_and_view.triggered.connect(
            tabs.toggle_edit_and_view
        )
        actions.shortcuts.triggered.connect(
            lambda: ShortcutsDialog(self, self.menuBar()).exec()
        )
        actions.about.triggered.connect(lambda: show_about(self))
        actions.show_in_file_browser.triggered.connect(
            self._locations.show_in_file_browser
        )
        actions.open_terminal_here.triggered.connect(
            self._locations.open_terminal
        )
        actions.open_command_prompt_here.triggered.connect(
            self._locations.open_command_prompt
        )
        actions.open_powershell_here.triggered.connect(
            self._locations.open_powershell
        )
        for name, action in actions.themes.items():
            action.triggered.connect(
                lambda _checked=False, theme=name: self.switch_theme(theme)
            )

    def connect_widgets(self) -> None:
        """Connect widget and command signals to the slots below."""
        tree = self._sidebar.tree
        tree.note_selected.connect(self.open_note)
        tree.note_browsed.connect(self.browse_note)
        tree.note_moved.connect(self._commands.move_note)
        tree.note_renamed.connect(self._commands.apply_note_rename)
        tree.category_renamed.connect(self._commands.apply_category_rename)
        tree.customContextMenuRequested.connect(self._locations.show_menu)
        self._sidebar.search_requested.connect(self.run_search)
        self._tabs.editor.save_due.connect(self.save_note)
        self._tabs.editor.images_offered.connect(
            self._clipboard.insert_images
        )
        self._tabs.preview.code_copied.connect(
            lambda: self.statusBar().showMessage("Copied code block")
        )
        self._tabs.preview.selection_copied.connect(
            self._clipboard.replace_selection_copy
        )
        self._clipboard.status_message.connect(self.statusBar().showMessage)
        self._commands.tree_changed.connect(self.refresh_tree)
        self._commands.note_created.connect(self.open_new_note)
        self._commands.status_message.connect(self.statusBar().showMessage)
        self._locations.status_message.connect(self.statusBar().showMessage)

    # --- Notes -----------------------------------------------------------

    def open_note(self, name: str) -> None:
        """Load a note and switch to the Edit tab, as a click does."""
        if self.load_note(name):
            self._tabs.show_edit_tab()

    def browse_note(self, name: str) -> None:
        """Load a note but stay on the current tab, re-rendering View.

        Used for arrow keys in the tree, so the user can step through
        rendered notes without being sent back to Edit each time.
        """
        if self.load_note(name):
            self._tabs.refresh_view()

    def load_note(self, name: str) -> bool:
        """Flush pending saves, put a note in the editor, return success."""
        self._tabs.flush_pending_saves()
        try:
            text = self._library.read_note(name)
        except (OSError, UnicodeDecodeError) as error:
            self.statusBar().showMessage(f"Could not open {name}: {error}")
            return False
        self._tabs.editor.open_note(name, text)
        self.update_title()
        return True

    def open_new_note(self, name: str) -> None:
        """Show a just-created note, clearing any search that hides it."""
        self._sidebar.clear_search()
        self.refresh_tree()
        self._sidebar.tree.select_note(name)
        self.open_note(name)
        self._tabs.editor.setFocus()

    def save_note(self, name: str, text: str) -> None:
        """Write a note; on failure the editor keeps it for a retry."""
        if not self.save_and_report(
            lambda: self._library.save_note(name, text)
        ):
            self._tabs.editor.save_failed(name)

    def switch_theme(self, name: str) -> None:
        """Apply a theme to the window and the View tab.

        An unknown or broken theme falls back to Default.
        """
        self._theme = self._themes.resolve(name)
        apply_theme(QApplication.instance(), self._themes.qss(self._theme))
        self._actions.themes[self._theme].setChecked(True)
        self._session.save_theme(self._theme)
        self._tabs.refresh_view()

    def save_and_report(self, write: Callable[[], None]) -> bool:
        """Run a save, show its time or its error, and return success."""
        try:
            write()
        except OSError as error:
            self.statusBar().showMessage(f"Save failed: {error}")
            return False
        saved_at = datetime.now().strftime(STATUS_TIME_FORMAT)
        self.statusBar().showMessage(f"Saved {saved_at}")
        return True

    # --- Search and editing ----------------------------------------------

    def run_search(self, query: str) -> None:
        """Flush pending text, then filter the tree to matching notes.

        An empty query clears the filter.
        """
        self._tabs.flush_pending_saves()
        if query:
            self._sidebar.tree.apply_filter(self._library.search(query))
        else:
            self._sidebar.tree.clear_filter()

    def edit_focused(self, method: str) -> None:
        """Run an Edit menu command on whichever text box has focus.

        The View tab counts as one for Copy and Select All. Focus there
        sits on a widget inside the web view, so the view stands in.
        """
        focus = QApplication.focusWidget()
        if focus is not None and self._tabs.preview.isAncestorOf(focus):
            focus = self._tabs.preview
        command = getattr(focus, method, None)
        if callable(command):
            command()

    def clean_up_images(self) -> None:
        """Move images no note links to into the trash and say how many."""
        self._tabs.flush_pending_saves()
        try:
            moved = self._library.clean_up_unused_images()
        except OSError as error:
            self.statusBar().showMessage(f"Clean up failed: {error}")
            return
        self.statusBar().showMessage(
            f"Moved {moved} unused image(s) to the trash"
        )

    # --- Housekeeping ----------------------------------------------------

    def refresh_tree(self) -> None:
        """Rebuild the sidebar tree from the Library, keeping any search."""
        self._sidebar.tree.populate(self._library.listings())
        self.run_search(self._sidebar.current_query())
        self.update_title()

    def update_title(self) -> None:
        """Show the open note's name in the window title."""
        name = self._tabs.editor.current_note_name()
        self.setWindowTitle(f"{name} - {APP_NAME}" if name else APP_NAME)

    def restore_session(self) -> None:
        """Restore window size, splitter position, and the last open note."""
        self._session.restore_layout(self, self._splitter)
        name = self._session.last_note()
        if name is not None and self._library.note_exists(name):
            self._sidebar.tree.select_note(name)
            self.open_note(name)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Flush pending saves and remember the session before closing.

        If something still could not be saved, ask before quitting, since
        closing would lose that text.
        """
        self._tabs.flush_pending_saves()
        if self._tabs.has_unsaved_changes() and not confirm(
            self,
            "Unsaved Changes",
            "Some changes could not be saved. Quit anyway and lose them?",
        ):
            event.ignore()
            return
        self._session.save(
            self, self._splitter, self._tabs.editor.current_note_name()
        )
        super().closeEvent(event)
