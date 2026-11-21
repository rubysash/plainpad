"""The Help > Keyboard Shortcuts window.

The table is read from the menu bar each time it opens, so it always
shows the keys the menus actually have. Keys that belong to a widget
rather than a menu come from ``config.WIDGET_SHORTCUTS``.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMenuBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from plainpad.config import (
    SHORTCUTS_COLUMNS,
    SHORTCUTS_DIALOG_SIZE,
    SHORTCUTS_DIALOG_TITLE,
    WIDGET_SHORTCUTS,
)


def menu_shortcuts(menu_bar: QMenuBar) -> list[tuple[str, str, str]]:
    """Return (menu, item, keys) for every menu item that has a key.

    Items are listed in menu order. Submenus are named by their path,
    such as "Settings > Theme".
    """
    rows: list[tuple[str, str, str]] = []
    pending = [(plain(a.text()), a) for a in menu_bar.actions()]
    while pending:
        where, menu_action = pending.pop(0)
        for action in menu_action.menu().actions():
            if action.menu() is not None:
                pending.append((f"{where} > {plain(action.text())}", action))
            elif not action.shortcut().isEmpty():
                rows.append((where, plain(action.text()), keys_of(action)))
    return rows


def plain(text: str) -> str:
    """Return a menu label without its ``&`` mnemonic marker."""
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&")


def keys_of(action: QAction) -> str:
    """Return an action's shortcut as the OS would write it."""
    native = QKeySequence.SequenceFormat.NativeText
    return action.shortcut().toString(native)


class ShortcutsDialog(QDialog):
    """A read-only table of every keyboard shortcut."""

    def __init__(self, parent: QWidget, menu_bar: QMenuBar) -> None:
        """Build the table from ``menu_bar`` and the widget-only keys."""
        super().__init__(parent)
        self.setWindowTitle(SHORTCUTS_DIALOG_TITLE)
        self.resize(*SHORTCUTS_DIALOG_SIZE)
        rows = menu_shortcuts(menu_bar) + list(WIDGET_SHORTCUTS)
        self.table = QTableWidget(len(rows), len(SHORTCUTS_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(SHORTCUTS_COLUMNS)
        for row, cells in enumerate(rows):
            for column, text in enumerate(cells):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().hide()
        # Where and Command fit their text and Keys takes the rest, so no
        # command name is cut short.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(buttons)
