"""GUI tests for Help > Keyboard Shortcuts, using pytest-qt."""

import pytest
from PyQt6.QtWidgets import QTableWidget

from plainpad.config import WIDGET_SHORTCUTS
from plainpad.gui.main_window import MainWindow
from plainpad.gui.shortcuts_dialog import ShortcutsDialog


def table_rows(table: QTableWidget) -> list[tuple[str, ...]]:
    """Return every row of a table as a tuple of cell texts."""
    return [
        tuple(
            table.item(row, column).text()
            for column in range(table.columnCount())
        )
        for row in range(table.rowCount())
    ]


def test_help_menu_offers_keyboard_shortcuts_on_f1(
    window: MainWindow,
) -> None:
    """Help lists Keyboard Shortcuts, bound to F1, above About."""
    help_menu = window.menuBar().actions()[-1].menu()
    labels = [a.text() for a in help_menu.actions() if not a.isSeparator()]
    assert labels == ["&Keyboard Shortcuts", "&About Plainpad"]
    assert help_menu.actions()[0].shortcut().toString() == "F1"


def test_table_lists_every_menu_key_and_widget_key(
    window: MainWindow,
) -> None:
    """Menu keys come from the menus; widget keys are appended."""
    dialog = ShortcutsDialog(window, window.menuBar())
    rows = table_rows(dialog.table)
    assert ("Edit", "Paste Formatted", "Ctrl+Shift+V") in rows
    assert ("File", "Rename", "F2") in rows
    assert ("Help", "Keyboard Shortcuts", "F1") in rows
    assert rows[-len(WIDGET_SHORTCUTS):] == list(WIDGET_SHORTCUTS)
    commands = [command for _where, command, _keys in rows]
    assert "Clean Up Unused Images" not in commands
    assert not any("&" in command for command in commands)
    dialog.deleteLater()


def test_shortcuts_action_opens_the_dialog(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Choosing the menu item opens the shortcuts table."""
    opened: list[int] = []
    monkeypatch.setattr(
        ShortcutsDialog,
        "exec",
        lambda self: opened.append(self.table.rowCount()) or 0,
    )
    window.menuBar().actions()[-1].menu().actions()[0].trigger()
    assert opened and opened[0] > len(WIDGET_SHORTCUTS)
