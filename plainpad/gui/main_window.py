"""The main window: layout and signal wiring, no business logic.

MainWindow owns the sidebar, the tab area, the menu actions, and the
status bar. Its slots translate widget signals into Library calls and then
tell the widgets what changed. Creating, renaming, moving, and deleting
notes and categories is delegated to TreeCommands.
"""

from collections.abc import Callable
from datetime import datetime

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter

from plainpad.config import APP_NAME, STATUS_TIME_FORMAT
from plainpad.gui.actions import Actions, populate_menu_bar
from plainpad.gui.dialogs import show_about
from plainpad.gui.session import SessionMemory
from plainpad.gui.sidebar import Sidebar
from plainpad.gui.tab_area import TabArea
from plainpad.gui.tree_commands import TreeCommands
from plainpad.library import Library
from plainpad.render import MarkdownRenderer
from plainpad.style_store import StyleStore


class MainWindow(QMainWindow):
    """Top-level window that connects every widget to the Library."""

    def __init__(self, library: Library, style_store: StyleStore) -> None:
        """Build the widgets, connect them, and restore the last session."""
        super().__init__()
        self._library = library
        self._style_store = style_store
        self._session = SessionMemory()
        self.build_layout()
        self._actions = Actions(self)
        populate_menu_bar(self.menuBar(), self._actions)
        self._commands = TreeCommands(
            library, self._sidebar.tree, self._tabs.editor, self
        )
        self.connect_actions()
        self.connect_widgets()
        self.refresh_tree()
        self.restore_session()

    # --- Construction ----------------------------------------------------

    def build_layout(self) -> None:
        """Create the splitter with the sidebar left and the tabs right."""
        self._sidebar = Sidebar(self)
        self._tabs = TabArea(
            MarkdownRenderer(),
            self._style_store.load(),
            self._style_store.default_css(),
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
        actions.find.triggered.connect(self._sidebar.focus_search)
        actions.show_edit_tab.triggered.connect(tabs.show_edit_tab)
        actions.show_view_tab.triggered.connect(tabs.show_view_tab)
        actions.show_settings_tab.triggered.connect(tabs.show_settings_tab)
        actions.toggle_edit_and_view.triggered.connect(
            tabs.toggle_edit_and_view
        )
        actions.about.triggered.connect(lambda: show_about(self))

    def connect_widgets(self) -> None:
        """Connect widget and command signals to the slots below."""
        tree = self._sidebar.tree
        tree.note_selected.connect(self.open_note)
        tree.note_moved.connect(self._commands.move_note)
        tree.note_renamed.connect(self._commands.apply_note_rename)
        tree.category_renamed.connect(self._commands.apply_category_rename)
        self._sidebar.search_requested.connect(self.run_search)
        self._tabs.editor.save_due.connect(self.save_note)
        self._tabs.settings.save_due.connect(self.save_css)
        self._commands.tree_changed.connect(self.refresh_tree)
        self._commands.note_created.connect(self.open_new_note)
        self._commands.status_message.connect(self.statusBar().showMessage)

    # --- Notes -----------------------------------------------------------

    def open_note(self, name: str) -> None:
        """Flush any pending save, then show a note in the Edit tab."""
        self._tabs.flush_pending_saves()
        try:
            text = self._library.read_note(name)
        except (OSError, UnicodeDecodeError) as error:
            self.statusBar().showMessage(f"Could not open {name}: {error}")
            return
        self._tabs.editor.open_note(name, text)
        self.update_title()
        self._tabs.show_edit_tab()

    def open_new_note(self, name: str) -> None:
        """Show a just-created note, clearing any search that hides it."""
        self._sidebar.clear_search()
        self.refresh_tree()
        self._sidebar.tree.select_note(name)
        self.open_note(name)
        self._tabs.editor.setFocus()

    def save_note(self, name: str, text: str) -> None:
        """Write a note and report success or failure in the status bar."""
        self.save_and_report(lambda: self._library.save_note(name, text))

    def save_css(self, css: str) -> None:
        """Write the preview CSS and report the result in the status bar."""
        self.save_and_report(lambda: self._style_store.save(css))

    def save_and_report(self, write: Callable[[], None]) -> None:
        """Run a save and show its time, or its error, in the status bar."""
        try:
            write()
        except OSError as error:
            self.statusBar().showMessage(f"Save failed: {error}")
            return
        saved_at = datetime.now().strftime(STATUS_TIME_FORMAT)
        self.statusBar().showMessage(f"Saved {saved_at}")

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
        """Run an Edit menu command on whichever text box has focus."""
        command = getattr(QApplication.focusWidget(), method, None)
        if callable(command):
            command()

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
        """Flush pending saves and remember the session before closing."""
        self._tabs.flush_pending_saves()
        self._session.save(
            self, self._splitter, self._tabs.editor.current_note_name()
        )
        super().closeEvent(event)
