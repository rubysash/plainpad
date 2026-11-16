"""Rows of the note tree: what a row is and how to read it back.

Each row carries a (kind, identity) pair in its item data: a category id
for category rows, a note name for note rows. Code that walks the tree
reads that pair instead of parsing the displayed text.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

KIND_CATEGORY = "category"
KIND_NOTE = "note"
IDENTITY_ROLE = Qt.ItemDataRole.UserRole

Flag = Qt.ItemFlag
CATEGORY_FLAGS = Flag.ItemIsEnabled | Flag.ItemIsSelectable | (
    Flag.ItemIsDropEnabled
)
EDITABLE_CATEGORY_FLAGS = CATEGORY_FLAGS | Flag.ItemIsEditable
NOTE_FLAGS = EDITABLE_CATEGORY_FLAGS | Flag.ItemIsDragEnabled


def make_item(
    parent: QTreeWidget | QTreeWidgetItem,
    text: str,
    kind: str,
    identity: str,
    flags: Qt.ItemFlag,
) -> QTreeWidgetItem:
    """Create a row under ``parent`` carrying its kind and identity."""
    item = QTreeWidgetItem(parent, [text])
    item.setData(0, IDENTITY_ROLE, (kind, identity))
    item.setFlags(flags)
    return item


def identity_of(item: QTreeWidgetItem) -> tuple[str, str]:
    """Return the (kind, identity) pair stored on a row."""
    return item.data(0, IDENTITY_ROLE)


def children_of(item: QTreeWidgetItem) -> list[QTreeWidgetItem]:
    """Return a row's child rows."""
    return [item.child(i) for i in range(item.childCount())]


def category_items(tree: QTreeWidget) -> list[QTreeWidgetItem]:
    """Return the top-level category rows of a tree."""
    return [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]


def expanded_category_ids(tree: QTreeWidget) -> set[str]:
    """Return the ids of the categories that are expanded now."""
    return {
        identity_of(item)[1]
        for item in category_items(tree)
        if item.isExpanded()
    }
