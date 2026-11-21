"""Menu items and their key bindings.

Every QAction is created here with its text and shortcut. MainWindow
connects each action's ``triggered`` signal; this module decides nothing
about what an action does.
"""

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtWidgets import QMenu, QMenuBar, QWidget

from plainpad.desktop_launch import DesktopLauncher
from plainpad.models import Theme


class Actions(QObject):
    """All QActions as named attributes.

    File: new_note, new_category, rename, delete, save_now,
          clean_up_images, exit
    Edit: undo, redo, cut, copy, copy_note_rich, paste, paste_formatted,
          select_all, find
    View: show_edit_tab, show_view_tab, toggle_edit_and_view
    Settings: themes, one checkable action per theme name
    Help: shortcuts, about
    Tree right-click menu: show_in_file_browser, open_terminal_here,
          open_command_prompt_here, open_powershell_here

    Shortcuts are listed in SPEC.md section 8.
    """

    def __init__(
        self, parent: QObject, themes: list[Theme], file_browser_label: str
    ) -> None:
        """Create every action with its label and shortcut.

        ``file_browser_label`` names the OS's file browser, such as
        "Show in Explorer".
        """
        super().__init__(parent)
        # Exclusive, so checking one theme unchecks the rest.
        self._theme_group = QActionGroup(self)
        self.themes: dict[str, QAction] = {}
        for theme in themes:
            action = self.make(theme.label, "")
            action.setCheckable(True)
            self._theme_group.addAction(action)
            self.themes[theme.name] = action
        self.new_note = self.make("&New Note", "Ctrl+N")
        self.new_category = self.make("New &Category", "Ctrl+Shift+N")
        self.rename = self.make("&Rename", "F2")
        self.delete = self.make("&Delete", "Del")
        # Del must keep working in the editor and search box, so it only
        # fires when a widget this action is added to (the tree) has focus.
        self.delete.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        self.save_now = self.make("&Save Now", "Ctrl+S")
        self.clean_up_images = self.make("Clean &Up Unused Images", "")
        self.exit = self.make("E&xit", "Ctrl+Q")

        self.undo = self.make("&Undo", "Ctrl+Z")
        self.redo = self.make("&Redo", "Ctrl+Y")
        self.cut = self.make("Cu&t", "Ctrl+X")
        self.copy = self.make("&Copy", "Ctrl+C")
        self.copy_note_rich = self.make(
            "Copy &Note as Rich Text", "Ctrl+Shift+C"
        )
        self.paste = self.make("&Paste", "Ctrl+V")
        self.paste_formatted = self.make("Paste For&matted", "Ctrl+Shift+V")
        self.select_all = self.make("Select &All", "Ctrl+A")
        self.find = self.make("&Find", "Ctrl+F")

        self.show_edit_tab = self.make("&Edit Tab", "Ctrl+1")
        self.show_view_tab = self.make("&View Tab", "Ctrl+2")
        self.toggle_edit_and_view = self.make("&Toggle Edit / View", "Ctrl+E")

        self.shortcuts = self.make("&Keyboard Shortcuts", "F1")
        self.about = self.make("&About Plainpad", "")

        self.show_in_file_browser = self.make(file_browser_label, "")
        self.open_terminal_here = self.make("Open &Terminal Here", "")
        self.open_command_prompt_here = self.make(
            "Open &Command Prompt Here", ""
        )
        self.open_powershell_here = self.make("Open &PowerShell Here", "")

    def make(self, text: str, shortcut: str) -> QAction:
        """Create one action owned by this object."""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        return action


def populate_menu_bar(menu_bar: QMenuBar, actions: Actions) -> None:
    """Add the File, Edit, View, and Help menus to a menu bar."""
    file_menu = menu_bar.addMenu("&File")
    file_menu.addActions([actions.new_note, actions.new_category])
    file_menu.addSeparator()
    file_menu.addActions([actions.rename, actions.delete])
    file_menu.addSeparator()
    file_menu.addAction(actions.save_now)
    file_menu.addSeparator()
    file_menu.addAction(actions.clean_up_images)
    file_menu.addSeparator()
    file_menu.addAction(actions.exit)

    edit_menu = menu_bar.addMenu("&Edit")
    edit_menu.addActions([actions.undo, actions.redo])
    edit_menu.addSeparator()
    edit_menu.addActions(
        [
            actions.cut,
            actions.copy,
            actions.copy_note_rich,
            actions.paste,
            actions.paste_formatted,
            actions.select_all,
        ]
    )
    edit_menu.addSeparator()
    edit_menu.addAction(actions.find)

    view_menu = menu_bar.addMenu("&View")
    view_menu.addActions([actions.show_edit_tab, actions.show_view_tab])
    view_menu.addSeparator()
    view_menu.addAction(actions.toggle_edit_and_view)

    settings_menu = menu_bar.addMenu("&Settings")
    theme_menu = settings_menu.addMenu("&Theme")
    theme_menu.addActions(list(actions.themes.values()))

    help_menu = menu_bar.addMenu("&Help")
    help_menu.addAction(actions.shortcuts)
    help_menu.addSeparator()
    help_menu.addAction(actions.about)


def build_tree_menu(
    parent: QWidget, actions: Actions, launcher: DesktopLauncher
) -> QMenu:
    """Return the menu shown when the note tree is right-clicked.

    New Note and New Category are the File menu's own actions. Only the
    shells this computer has are offered: Command Prompt and PowerShell
    on Windows, and a terminal if one is installed.
    """
    menu = QMenu(parent)
    menu.addActions([actions.new_note, actions.new_category])
    menu.addSeparator()
    menu.addAction(actions.show_in_file_browser)
    menu.addSeparator()
    if launcher.has_terminal():
        menu.addAction(actions.open_terminal_here)
    if launcher.offers_windows_shells():
        menu.addActions(
            [actions.open_command_prompt_here, actions.open_powershell_here]
        )
    return menu
