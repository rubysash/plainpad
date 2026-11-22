"""Tests for plainpad.images, plainpad.image_links, and the binary
atomic write. Every test uses pytest's tmp_path."""

from pathlib import Path

import pytest

from plainpad.atomic_file import write_bytes_atomically
from plainpad.config import IMAGE_HASH_LENGTH
from plainpad.image_links import (
    image_link_for,
    image_names_in,
    stored_image_name,
)
from plainpad.images import ImageFormatError, ImageStore, image_extension
from tests.image_samples import GIF, JPEG, NOT_AN_IMAGE, PNG, WEBP


@pytest.fixture
def store(tmp_path: Path) -> ImageStore:
    """An ImageStore over folders that do not exist yet."""
    return ImageStore(tmp_path / "images", tmp_path / "trash" / "images")


@pytest.mark.parametrize(
    ("data", "extension"),
    [(PNG, ".png"), (JPEG, ".jpg"), (GIF, ".gif"), (WEBP, ".webp")],
)
def test_extension_comes_from_content(data: bytes, extension: str) -> None:
    assert image_extension(data) == extension


def test_non_image_is_refused(store: ImageStore) -> None:
    with pytest.raises(ImageFormatError):
        store.add(NOT_AN_IMAGE)
    assert store.names() == []


def test_oversized_image_is_refused(
    store: ImageStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("plainpad.images.IMAGE_MAX_BYTES", len(PNG) - 1)
    with pytest.raises(ImageFormatError):
        store.add(PNG)


def test_add_keeps_exact_bytes_under_hash_name(store: ImageStore) -> None:
    name = store.add(GIF)
    stem, extension = name.split(".")
    assert len(stem) == IMAGE_HASH_LENGTH
    assert extension == "gif"
    assert store.read(name) == GIF


def test_same_image_twice_is_one_file(store: ImageStore) -> None:
    assert store.add(PNG) == store.add(PNG)
    assert len(store.names()) == 1


def test_trash_unused_moves_only_unreferenced(
    store: ImageStore, tmp_path: Path
) -> None:
    kept, unused = store.add(PNG), store.add(GIF)
    # Referenced in another case, as a hand-edited link might be.
    assert store.trash_unused({kept.upper()}) == 1
    assert store.names() == [kept]
    assert (tmp_path / "trash" / "images" / unused).read_bytes() == GIF


def test_trash_unused_twice_does_not_fail(store: ImageStore) -> None:
    store.add(PNG)
    store.trash_unused(set())
    store.add(PNG)
    assert store.trash_unused(set()) == 1
    assert store.names() == []


def test_write_bytes_atomically_leaves_no_temp_file(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "picture.png"
    write_bytes_atomically(target, PNG)
    assert target.read_bytes() == PNG
    assert [path.name for path in target.parent.iterdir()] == ["picture.png"]


def test_link_round_trip() -> None:
    link = image_link_for("0123456789abcdef.png")
    assert link == "![](../images/0123456789abcdef.png)"
    assert image_names_in(f"before {link} after") == {"0123456789abcdef.png"}


def test_links_are_found_in_raw_html_too() -> None:
    text = '<img src="../images/aa11.gif"> and ![x](../images/bb22.jpg "t")'
    assert image_names_in(text) == {"aa11.gif", "bb22.jpg"}


def test_only_the_exact_relative_link_is_a_stored_image() -> None:
    assert stored_image_name("../images/aa11.gif") == "aa11.gif"
    assert stored_image_name("https://example.com/../images/aa11.gif") is None
    assert stored_image_name("../images/aa11.gif?x=1") is None
