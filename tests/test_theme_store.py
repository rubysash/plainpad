"""Tests for plainpad.theme_store, against the shipped themes folder and
against made-up folders in tmp_path."""

import hashlib
from pathlib import Path

import pytest

from plainpad.config import DEFAULT_THEME, THEMES_DIR
from plainpad.theme_store import ThemeStore

# The Default theme must never change; it is the safe fallback. If a
# change is truly intended, update these hashes in the same commit.
DEFAULT_THEME_HASHES = {
    "app.qss": (
        "b1077ec8292c3e90f72f86eb6f118145251f8fc6f697e57313cc3453df287224"
    ),
    "preview.css": (
        "70a23a0aee83277065c87da14023618096c9628cbc0e715680573d280b377fde"
    ),
}


@pytest.fixture
def shipped() -> ThemeStore:
    """The themes that ship with the app."""
    return ThemeStore(THEMES_DIR)


def make_theme(root: Path, name: str, label: str | None = None) -> None:
    """Create a complete theme folder, with an optional theme.json."""
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "app.qss").write_text(f"/* {name} qss */", encoding="utf-8")
    (folder / "preview.css").write_text(f"/* {name} */", encoding="utf-8")
    if label is not None:
        (folder / "theme.json").write_text(
            f'{{"label": "{label}"}}', encoding="utf-8"
        )


@pytest.mark.parametrize("file_name", sorted(DEFAULT_THEME_HASHES))
def test_default_theme_is_unchanged(file_name: str) -> None:
    data = (THEMES_DIR / DEFAULT_THEME / file_name).read_bytes()
    # Normalize line endings so a git checkout setting cannot break this.
    digest = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    assert digest == DEFAULT_THEME_HASHES[file_name]


def test_shipped_themes_with_default_first(shipped: ThemeStore) -> None:
    names = [theme.name for theme in shipped.themes()]
    assert names[0] == DEFAULT_THEME
    assert set(names) == {"default", "crt", "dark", "light"}


def test_shipped_labels_come_from_theme_json(shipped: ThemeStore) -> None:
    labels = {theme.name: theme.label for theme in shipped.themes()}
    assert labels["dark"] == "Dark (Darkly)"


def test_every_shipped_theme_styles_the_copy_link(
    shipped: ThemeStore,
) -> None:
    for theme in shipped.themes():
        assert ".copy-code" in shipped.preview_css(theme.name)
        assert "QTreeWidget QLineEdit" in shipped.qss(theme.name)


def test_unknown_theme_resolves_to_default(shipped: ThemeStore) -> None:
    assert shipped.resolve("no-such-theme") == DEFAULT_THEME
    assert shipped.resolve(None) == DEFAULT_THEME
    assert shipped.resolve("dark") == "dark"
    assert shipped.qss("no-such-theme") == shipped.qss(DEFAULT_THEME)


def test_incomplete_folder_is_not_a_theme(tmp_path: Path) -> None:
    make_theme(tmp_path, "default")
    (tmp_path / "half").mkdir()
    (tmp_path / "half" / "app.qss").write_text("", encoding="utf-8")
    store = ThemeStore(tmp_path)
    assert [theme.name for theme in store.themes()] == ["default"]
    assert store.resolve("half") == "default"


def test_missing_label_falls_back_to_folder_name(tmp_path: Path) -> None:
    make_theme(tmp_path, "default", "Default")
    make_theme(tmp_path, "solarized")
    store = ThemeStore(tmp_path)
    labels = [theme.label for theme in store.themes()]
    assert labels == ["Default", "Solarized"]
