"""Search filtering for the note tree.

While a search is active, rows that do not match are hidden and the
categories holding matches are expanded. The expanded state from before
the search is remembered so clearing the search puts it back.
"""

from PyQt6.QtWidgets import QTreeWidget

from plainpad.gui.tree_items import (
    category_items,
    children_of,
    expanded_category_ids,
    identity_of,
)


class TreeFilter:
    """Hides and shows rows of one tree, and remembers what to restore."""

    def __init__(self, tree: QTreeWidget) -> None:
        """Attach to a tree; no filter is active yet."""
        self._tree = tree
        self._pre_filter_expanded: set[str] | None = None

    def apply(self, matching_note_names: set[str]) -> None:
        """Show only matching notes and expand the categories holding them.

        Categories without a match are hidden. The expanded state is
        recorded only on the first call of a search, so refiltering while
        a search is active does not overwrite it.
        """
        if self._pre_filter_expanded is None:
            self._pre_filter_expanded = expanded_category_ids(self._tree)
        for category_item in category_items(self._tree):
            any_match = False
            for note_item in children_of(category_item):
                matches = identity_of(note_item)[1] in matching_note_names
                note_item.setHidden(not matches)
                any_match = any_match or matches
            category_item.setHidden(not any_match)
            category_item.setExpanded(any_match)

    def clear(self) -> None:
        """Show every row and restore the pre-search expanded state."""
        if self._pre_filter_expanded is None:
            return
        for category_item in category_items(self._tree):
            category_item.setHidden(False)
            for note_item in children_of(category_item):
                note_item.setHidden(False)
            category_id = identity_of(category_item)[1]
            category_item.setExpanded(
                category_id in self._pre_filter_expanded
            )
        self._pre_filter_expanded = None
