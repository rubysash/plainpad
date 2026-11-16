"""Tests for plainpad.categories. Every test uses pytest's tmp_path."""

import json
from pathlib import Path

import pytest

from plainpad.categories import CategoryIndex, CategoryNameError
from plainpad.config import UNCATEGORIZED_ID, UNCATEGORIZED_NAME


@pytest.fixture
def index_file(tmp_path: Path) -> Path:
    """Where the index lives; the file does not exist yet."""
    return tmp_path / "index.json"


@pytest.fixture
def index(index_file: Path) -> CategoryIndex:
    """An empty index."""
    return CategoryIndex(index_file)


def names_of(index: CategoryIndex) -> list[str]:
    """Return the display names in listing order."""
    return [category.name for category in index.categories()]


def test_missing_file_loads_as_empty(index: CategoryIndex) -> None:
    assert names_of(index) == [UNCATEGORIZED_NAME]


def test_categories_sorted_with_uncategorized_last(
    index: CategoryIndex,
) -> None:
    for name in ("work", "Recipes", "art"):
        index.add(name)
    assert names_of(index) == ["art", "Recipes", "work", UNCATEGORIZED_NAME]


@pytest.mark.parametrize("bad_name", ["", "   ", "recipes", "uncategorized"])
def test_add_rejects_empty_and_duplicate_names(
    index: CategoryIndex, bad_name: str
) -> None:
    index.add("Recipes")
    with pytest.raises(CategoryNameError):
        index.add(bad_name)


def test_rename_keeps_id_and_notes(index: CategoryIndex) -> None:
    category = index.add("Recipes")
    index.assign("chili", category.category_id)
    index.rename(category.category_id, "Food")
    assert names_of(index) == ["Food", UNCATEGORIZED_NAME]
    assert index.category_of("chili") == category.category_id


def test_rename_and_remove_refuse_uncategorized(
    index: CategoryIndex,
) -> None:
    with pytest.raises(CategoryNameError):
        index.rename(UNCATEGORIZED_ID, "Other")
    with pytest.raises(CategoryNameError):
        index.remove(UNCATEGORIZED_ID)


def test_remove_sends_notes_to_uncategorized(index: CategoryIndex) -> None:
    category = index.add("Recipes")
    index.assign("chili", category.category_id)
    index.remove(category.category_id)
    assert names_of(index) == [UNCATEGORIZED_NAME]
    assert index.category_of("chili") == UNCATEGORIZED_ID


def test_unassigned_note_is_uncategorized(index: CategoryIndex) -> None:
    assert index.category_of("anything") == UNCATEGORIZED_ID


def test_assign_replaces_previous_assignment(index: CategoryIndex) -> None:
    first = index.add("First")
    second = index.add("Second")
    index.assign("note", first.category_id)
    index.assign("note", second.category_id)
    assert index.category_of("note") == second.category_id


def test_assign_to_uncategorized_removes_mapping(
    index: CategoryIndex, index_file: Path
) -> None:
    category = index.add("Recipes")
    index.assign("chili", category.category_id)
    index.assign("chili", UNCATEGORIZED_ID)
    stored = json.loads(index_file.read_text(encoding="utf-8"))
    assert stored["assignments"] == {}


def test_rename_note_and_forget_note(index: CategoryIndex) -> None:
    category = index.add("Recipes")
    index.assign("chili", category.category_id)
    index.rename_note("chili", "Chili con carne")
    assert index.category_of("Chili con carne") == category.category_id
    assert index.category_of("chili") == UNCATEGORIZED_ID
    index.forget_note("Chili con carne")
    assert index.category_of("Chili con carne") == UNCATEGORIZED_ID


def test_reconcile_drops_missing_notes(index: CategoryIndex) -> None:
    category = index.add("Recipes")
    index.assign("kept", category.category_id)
    index.assign("gone", category.category_id)
    index.reconcile(["kept"])
    assert index.category_of("kept") == category.category_id
    assert index.category_of("gone") == UNCATEGORIZED_ID


def test_changes_survive_reload(
    index: CategoryIndex, index_file: Path
) -> None:
    category = index.add("Recipes")
    index.assign("chili", category.category_id)
    reloaded = CategoryIndex(index_file)
    assert names_of(reloaded) == ["Recipes", UNCATEGORIZED_NAME]
    assert reloaded.category_of("chili") == category.category_id


def test_corrupt_index_is_set_aside(index_file: Path) -> None:
    index_file.write_text("{ not json", encoding="utf-8")
    index = CategoryIndex(index_file)
    assert names_of(index) == [UNCATEGORIZED_NAME]
    assert not index_file.exists()
    backups = list(index_file.parent.glob("index.json.*.corrupt"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{ not json"
