"""Plain data classes passed between the storage layer and the GUI."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    """A user-defined topic that notes can be filed under.

    The id never changes. The name is what the user sees and may be
    renamed freely.
    """

    category_id: str
    name: str


@dataclass
class CategoryListing:
    """One category together with the names of the notes inside it.

    This is the shape the sidebar tree is built from.
    """

    category: Category
    note_names: list[str] = field(default_factory=list)
