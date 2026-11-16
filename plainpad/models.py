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


@dataclass(frozen=True)
class Theme:
    """A look for the app: a folder name and the label shown in the menu."""

    name: str
    label: str


@dataclass(frozen=True)
class RenderedPage:
    """A note rendered for the View tab.

    ``code_blocks`` holds the plain text of each code block in page order;
    the page's Nth copy link refers to the Nth entry.
    """

    html: str
    code_blocks: list[str]


@dataclass
class CategoryListing:
    """One category together with the names of the notes inside it.

    This is the shape the sidebar tree is built from.
    """

    category: Category
    note_names: list[str] = field(default_factory=list)
