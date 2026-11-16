"""Tests for plainpad.crud. Every test uses pytest's tmp_path."""

from datetime import datetime
from pathlib import Path

import pytest

from plainpad.crud import NoteNameError, NoteStore, timestamp_name

FIXED_TIME = datetime(2026, 11, 16, 14, 30, 5)
FIXED_NAME = "2026-11-16_143005"


@pytest.fixture
def store(tmp_path: Path) -> NoteStore:
    """A NoteStore over empty folders."""
    return NoteStore(tmp_path / "notes", tmp_path / "trash")


def test_timestamp_name_formats_fixed_time() -> None:
    assert timestamp_name(FIXED_TIME) == FIXED_NAME


def test_create_makes_empty_file(store: NoteStore) -> None:
    name = store.create(FIXED_TIME)
    assert name == FIXED_NAME
    assert store.path_of(name).is_file()
    assert store.read(name) == ""


def test_create_appends_suffix_when_taken(store: NoteStore) -> None:
    store.create(FIXED_TIME)
    assert store.create(FIXED_TIME) == f"{FIXED_NAME}-2"
    assert store.create(FIXED_TIME) == f"{FIXED_NAME}-3"


def test_write_then_read_round_trips_non_ascii(store: NoteStore) -> None:
    text = "# Café\n\nnaïve — 日本語 ✓\n"
    store.write("note", text)
    assert store.read("note") == text


def test_write_leaves_no_temporary_file(
    store: NoteStore, tmp_path: Path
) -> None:
    store.write("note", "text")
    store.write("note", "more text")
    assert list((tmp_path / "notes").iterdir()) == [store.path_of("note")]


def test_names_sorted_ignoring_case_and_non_md(
    store: NoteStore, tmp_path: Path
) -> None:
    for name in ("banana", "Apple", "cherry"):
        store.write(name, "")
    (tmp_path / "notes" / "readme.txt").write_text("x")
    assert store.names() == ["Apple", "banana", "cherry"]


def test_rename_moves_file_and_keeps_text(store: NoteStore) -> None:
    store.write("old", "body")
    store.rename("old", "new")
    assert store.names() == ["new"]
    assert store.read("new") == "body"


@pytest.mark.parametrize(
    "bad_name",
    ["", "   ", "a/b", "a\\b", "a:b", "a*b", 'a"b', "a<b", "a|b", "tab\there",
     "CON", "nul", "com1", "LPT9", "aux.backup"],
)
def test_rename_rejects_bad_names(store: NoteStore, bad_name: str) -> None:
    store.write("note", "")
    with pytest.raises(NoteNameError):
        store.rename("note", bad_name)
    assert store.names() == ["note"]


def test_rename_rejects_existing_name(store: NoteStore) -> None:
    store.write("one", "")
    store.write("two", "")
    with pytest.raises(NoteNameError):
        store.rename("one", "two")


def test_rename_rejects_name_differing_only_by_case(
    store: NoteStore,
) -> None:
    store.write("Chili", "")
    store.write("soup", "")
    with pytest.raises(NoteNameError):
        store.rename("soup", "chili")


def test_rename_allows_changing_case_of_own_name(store: NoteStore) -> None:
    store.write("chili", "beans")
    store.rename("chili", "Chili")
    assert store.names() == ["Chili"]
    assert store.read("Chili") == "beans"


def test_delete_moves_file_to_trash(store: NoteStore, tmp_path: Path) -> None:
    store.write("note", "keep me")
    store.delete("note")
    assert store.names() == []
    trashed = tmp_path / "trash" / "note.md"
    assert trashed.read_text(encoding="utf-8") == "keep me"


def test_delete_does_not_overwrite_trashed_file(
    store: NoteStore, tmp_path: Path
) -> None:
    store.write("note", "first")
    store.delete("note")
    store.write("note", "second")
    store.delete("note")
    trashed = sorted(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "trash").iterdir()
    )
    assert trashed == ["first", "second"]
