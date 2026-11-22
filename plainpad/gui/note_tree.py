"""The collapsible category tree with drag and drop and search filtering.

Top-level items are categories and their children are notes. Each item
stores what it is (category or note) and its identity in item data, so the
displayed text is never parsed; see tree_items.py.
"""

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDropEvent, QKeyEvent
from PyQt6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem
from PyQt6.QtWidgets import QWidget

from plainpad.config import NOTE_BROWSE_DELAY_MS, UNCATEGORIZED_ID
from plainpad.gui.tree_filter import TreeFilter
from plainpad.gui.tree_items import (
    CATEGORY_FLAGS,
    EDITABLE_CATEGORY_FLAGS,
    KIND_CATEGORY,
    KIND_NOTE,
    NOTE_FLAGS,
    Flag,
    category_items,
    children_of,
    expanded_category_ids,
    identity_of,
    make_item,
)
from plainpad.models import CategoryListing

# Keys that move the selection; moving with them browses notes.
BROWSE_KEYS = frozenset(
    {
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_PageUp,
        Qt.Key.Key_PageDown,
        Qt.Key.Key_Home,
        Qt.Key.Key_End,
    }
)


class NoteTree(QTreeWidget):
    """Tree of categories and notes.

    The tree only reports what the user did. It never changes stored data
    itself; MainWindow applies the change and calls ``populate`` again.
    Signals that lead to a rebuild are emitted on the next event loop
    turn, because Qt must not have items deleted while it is still
    finishing an edit or a drop on them.
    """

    # A note was clicked: note name.
    note_selected = pyqtSignal(str)
    # The keyboard came to rest on a note after a short pause: note name.
    note_browsed = pyqtSignal(str)
    # A note was dropped on a category: note name, target category id.
    note_moved = pyqtSignal(str, str)
    # An in-place rename was committed: old note name, new note name.
    note_renamed = pyqtSignal(str, str)
    # An in-place rename was committed: category id, new name.
    category_renamed = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Configure a headerless single-selection tree that accepts
        internal drops."""
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        # A click toggles a category; double-click would toggle it back.
        self.setExpandsOnDoubleClick(False)
        # Renaming starts only from the F2 action, never from a click.
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # MainWindow supplies the right-click menu.
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        root = self.invisibleRootItem()
        root.setFlags(root.flags() & ~Flag.ItemIsDropEnabled)
        self._filter = TreeFilter(self)
        # Waiting for a pause keeps fast arrowing from loading every note.
        self._browse_delay = QTimer(self)
        self._browse_delay.setSingleShot(True)
        self._browse_delay.setInterval(NOTE_BROWSE_DELAY_MS)
        self._browse_delay.timeout.connect(self.announce_browsed_note)
        self.itemClicked.connect(self.on_item_clicked)
        self.itemActivated.connect(self.on_item_activated)
        self.itemChanged.connect(self.on_item_changed)

    def populate(self, listings: list[CategoryListing]) -> None:
        """Rebuild the tree.

        Categories that were expanded stay expanded, and the selected row
        stays selected. On first use every category is collapsed.
        """
        expanded = expanded_category_ids(self)
        selected = self.selected_item()
        selected_identity = identity_of(selected) if selected else None
        # Building items emits itemChanged, which would look like renames.
        self.blockSignals(True)
        self.clear()
        for listing in listings:
            category_id = listing.category.category_id
            flags = EDITABLE_CATEGORY_FLAGS
            if category_id == UNCATEGORIZED_ID:
                flags = CATEGORY_FLAGS
            parent = make_item(
                self, listing.category.name, KIND_CATEGORY, category_id, flags
            )
            for name in listing.note_names:
                make_item(parent, name, KIND_NOTE, name, NOTE_FLAGS)
            parent.setExpanded(category_id in expanded)
        self.blockSignals(False)
        restored = selected_identity and self.find_item(*selected_identity)
        if restored:
            self.setCurrentItem(restored)

    def select_note(self, name: str) -> None:
        """Select a note's row and expand the category that holds it."""
        item = self.find_item(KIND_NOTE, name)
        if item is None:
            return
        item.parent().setExpanded(True)
        self.setCurrentItem(item)
        self.scrollToItem(item)

    def selected_note_name(self) -> str | None:
        """Return the selected note's name, or None if no note is
        selected."""
        item = self.selected_item()
        if item is None or identity_of(item)[0] != KIND_NOTE:
            return None
        return identity_of(item)[1]

    def note_name_at(self, position: QPoint) -> str | None:
        """Return the name of the note at a viewport position, or None
        if a category or empty space is there."""
        item = self.itemAt(position)
        if item is None or identity_of(item)[0] != KIND_NOTE:
            return None
        return identity_of(item)[1]

    def selected_category_id(self) -> str | None:
        """Return the selected category's id.

        If a note is selected, this is the category that contains it, so
        a new note can be created beside the selected one.
        """
        item = self.selected_item()
        if item is None:
            return None
        if identity_of(item)[0] == KIND_NOTE:
            item = item.parent()
        return identity_of(item)[1]

    def selected_label(self) -> str | None:
        """Return the displayed text of the selected row, or None."""
        item = self.selected_item()
        return item.text(0) if item else None

    def category_is_selected(self) -> bool:
        """Return True if the selected row is a category, not a note."""
        item = self.selected_item()
        return item is not None and identity_of(item)[0] == KIND_CATEGORY

    def edit_selected(self) -> None:
        """Begin in-place rename of the selected row.

        Does nothing for the Uncategorized row.
        """
        item = self.selected_item()
        if item is not None and item.flags() & Flag.ItemIsEditable:
            self.editItem(item, 0)

    def apply_filter(self, matching_note_names: set[str]) -> None:
        """Show only matching notes; see TreeFilter.apply."""
        self._filter.apply(matching_note_names)

    def clear_filter(self) -> None:
        """Show every row and restore the pre-search expanded state."""
        self._filter.clear()

    def dropEvent(self, event: QDropEvent) -> None:
        """Turn a drop into a ``note_moved`` signal.

        Only notes can be dragged. The target is the category row under
        the cursor, or the category of the note under the cursor. Qt's own
        item move is not performed; the tree is rebuilt by MainWindow.
        """
        # Ignoring the drop stops Qt from moving or removing the item.
        event.ignore()
        source = self.selected_item()
        target = self.itemAt(event.position().toPoint())
        if source is None or target is None:
            return
        if identity_of(source)[0] != KIND_NOTE:
            return
        if identity_of(target)[0] == KIND_NOTE:
            target = target.parent()
        if target is source.parent():
            return
        note_name = identity_of(source)[1]
        category_id = identity_of(target)[1]
        QTimer.singleShot(
            0, lambda: self.note_moved.emit(note_name, category_id)
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Move as usual; after a pause, announce the note landed on."""
        super().keyPressEvent(event)
        if event.key() in BROWSE_KEYS:
            self._browse_delay.start()

    def announce_browsed_note(self) -> None:
        """Emit ``note_browsed`` if the selection rests on a note."""
        name = self.selected_note_name()
        if name is not None:
            self.note_browsed.emit(name)

    def on_item_clicked(self, item: QTreeWidgetItem) -> None:
        """Toggle a clicked category, or announce a clicked note."""
        kind, identity = identity_of(item)
        if kind == KIND_CATEGORY:
            item.setExpanded(not item.isExpanded())
        else:
            self.note_selected.emit(identity)

    def on_item_activated(self, item: QTreeWidgetItem) -> None:
        """Open a note when Enter is pressed on it."""
        kind, identity = identity_of(item)
        if kind == KIND_NOTE:
            self.note_selected.emit(identity)

    def on_item_changed(self, item: QTreeWidgetItem) -> None:
        """Report a committed in-place rename."""
        kind, identity = identity_of(item)
        new_text = item.text(0).strip()
        signal = self.note_renamed if kind == KIND_NOTE else (
            self.category_renamed
        )
        QTimer.singleShot(0, lambda: signal.emit(identity, new_text))

    def selected_item(self) -> QTreeWidgetItem | None:
        """Return the single selected row, or None."""
        items = self.selectedItems()
        return items[0] if items else None

    def find_item(self, kind: str, identity: str) -> QTreeWidgetItem | None:
        """Return the row for a category id or note name, or None."""
        for category_item in category_items(self):
            if identity_of(category_item) == (kind, identity):
                return category_item
            for note_item in children_of(category_item):
                if identity_of(note_item) == (kind, identity):
                    return note_item
        return None
