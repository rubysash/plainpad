"""Tests for plainpad.library. Every test uses pytest's tmp_path."""

import json
from pathlib import Path

import pytest

from plainpad.config import UNCATEGORIZED_ID, UNCATEGORIZED_NAME
from plainpad.library import Library, NoteNameError


@pytest.fixture
def library(tmp_path: Path) -> Library:
    """A Library over a data folder that does not exist yet."""
    return Library(tmp_path / "data")


def notes_by_category(library: Library) -> dict[str, list[str]]:
    """Return {category name: note names} from the listings."""
    return {
        listing.category.name: listing.note_names
        for listing in library.listings()
    }


def test_new_data_folder_is_created(library: Library, tmp_path: Path) -> None:
    assert (tmp_path / "data" / "notes").is_dir()
    assert (tmp_path / "data" / "trash").is_dir()
    assert notes_by_category(library) == {UNCATEGORIZED_NAME: []}


def test_create_note_goes_into_requested_category(library: Library) -> None:
    recipes = library.create_category("Recipes")
    name = library.create_note(recipes.category_id)
    assert notes_by_category(library) == {
        "Recipes": [name],
        UNCATEGORIZED_NAME: [],
    }
    assert library.read_note(name) == ""


def test_create_note_in_uncategorized(library: Library) -> None:
    name = library.create_note(UNCATEGORIZED_ID)
    assert notes_by_category(library) == {UNCATEGORIZED_NAME: [name]}


def test_rename_note_keeps_category(library: Library) -> None:
    recipes = library.create_category("Recipes")
    name = library.create_note(recipes.category_id)
    library.rename_note(name, "Chili")
    assert notes_by_category(library)["Recipes"] == ["Chili"]
    assert library.note_exists("chili")


def test_rename_note_rejects_bad_name(library: Library) -> None:
    name = library.create_note(UNCATEGORIZED_ID)
    with pytest.raises(NoteNameError):
        library.rename_note(name, "a:b")


def test_delete_note_removes_from_listings_and_index(
    library: Library, tmp_path: Path
) -> None:
    recipes = library.create_category("Recipes")
    name = library.create_note(recipes.category_id)
    library.delete_note(name)
    assert notes_by_category(library)["Recipes"] == []
    index = json.loads((tmp_path / "data" / "index.json").read_text())
    assert index["assignments"] == {}
    assert (tmp_path / "data" / "trash" / f"{name}.md").is_file()


def test_move_note_changes_listing(library: Library) -> None:
    recipes = library.create_category("Recipes")
    library.save_note("Chili", "beans")
    library.move_note("Chili", recipes.category_id)
    assert notes_by_category(library) == {
        "Recipes": ["Chili"],
        UNCATEGORIZED_NAME: [],
    }


def test_delete_category_moves_notes_to_uncategorized(
    library: Library,
) -> None:
    recipes = library.create_category("Recipes")
    library.save_note("Chili", "beans")
    library.move_note("Chili", recipes.category_id)
    library.delete_category(recipes.category_id)
    assert notes_by_category(library) == {UNCATEGORIZED_NAME: ["Chili"]}


def test_hand_added_file_is_uncategorized(tmp_path: Path) -> None:
    notes_dir = tmp_path / "data" / "notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "by hand.md").write_text("hello", encoding="utf-8")
    library = Library(tmp_path / "data")
    assert notes_by_category(library) == {UNCATEGORIZED_NAME: ["by hand"]}


def test_index_entry_for_missing_file_is_dropped(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    index_file = data_dir / "index.json"
    index_file.write_text(
        json.dumps(
            {
                "version": 1,
                "categories": [{"id": "3f9a1c2e", "name": "Recipes"}],
                "assignments": {"vanished": "3f9a1c2e"},
            }
        ),
        encoding="utf-8",
    )
    library = Library(data_dir)
    assert notes_by_category(library) == {
        "Recipes": [],
        UNCATEGORIZED_NAME: [],
    }
    stored = json.loads(index_file.read_text(encoding="utf-8"))
    assert stored["assignments"] == {}


def test_search_goes_through_library(library: Library) -> None:
    library.save_note("Chili", "Beans and cumin")
    assert library.search("CUMIN") == {"Chili"}
