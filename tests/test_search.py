"""Tests for plainpad.search. Every test uses pytest's tmp_path."""

from pathlib import Path

import pytest

from plainpad.crud import NoteStore
from plainpad.search import find_matching_notes


@pytest.fixture
def store(tmp_path: Path) -> NoteStore:
    """A store holding two notes."""
    store = NoteStore(tmp_path / "notes", tmp_path / "trash")
    store.write("Chili", "Beans, tomatoes, and cumin.")
    store.write("Shopping", "Milk\nEggs\n")
    return store


def test_matches_body_text(store: NoteStore) -> None:
    assert find_matching_notes(store, "cumin") == {"Chili"}


def test_matches_note_name(store: NoteStore) -> None:
    assert find_matching_notes(store, "shop") == {"Shopping"}


def test_matching_ignores_case(store: NoteStore) -> None:
    assert find_matching_notes(store, "EGGS") == {"Shopping"}
    assert find_matching_notes(store, "chili") == {"Chili"}


@pytest.mark.parametrize("query", ["", "   ", "\t"])
def test_blank_query_matches_nothing(store: NoteStore, query: str) -> None:
    assert find_matching_notes(store, query) == set()


def test_no_hits_returns_empty_set(store: NoteStore) -> None:
    assert find_matching_notes(store, "zebra") == set()


def test_non_utf8_note_matches_on_name_only(
    store: NoteStore, tmp_path: Path
) -> None:
    (tmp_path / "notes" / "legacy.md").write_bytes(b"caf\xe9")
    assert find_matching_notes(store, "legacy") == {"legacy"}
    assert find_matching_notes(store, "caf") == set()
