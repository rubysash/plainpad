"""Tests for plainpad.style_store. Every test uses pytest's tmp_path."""

from pathlib import Path

import pytest

from plainpad.style_store import StyleStore
from plainpad.theme_store import ThemeStore


@pytest.fixture
def style_store(tmp_path: Path) -> StyleStore:
    """A StyleStore over two made-up themes and no user CSS yet."""
    themes_dir = tmp_path / "themes"
    for name in ("default", "dark"):
        folder = themes_dir / name
        folder.mkdir(parents=True)
        (folder / "app.qss").write_text("", encoding="utf-8")
        (folder / "preview.css").write_text(
            f"/* {name} */", encoding="utf-8"
        )
    return StyleStore(tmp_path / "data" / "styles", ThemeStore(themes_dir))


def test_load_returns_shipped_css_when_nothing_saved(
    style_store: StyleStore,
) -> None:
    assert style_store.load("dark") == "/* dark */"


def test_save_then_load_returns_saved_css(style_store: StyleStore) -> None:
    style_store.save("dark", "p { margin: 0; }")
    assert style_store.load("dark") == "p { margin: 0; }"
    assert style_store.default_css("dark") == "/* dark */"


def test_each_theme_keeps_its_own_css(
    tmp_path: Path, style_store: StyleStore
) -> None:
    style_store.save("dark", "dark custom")
    assert style_store.load("default") == "/* default */"
    assert (tmp_path / "data" / "styles" / "dark.css").is_file()


def test_default_theme_is_read_only(
    tmp_path: Path, style_store: StyleStore
) -> None:
    assert not style_store.is_editable("default")
    with pytest.raises(ValueError):
        style_store.save("default", "broken")
    # Even a file planted by hand is ignored for Default.
    planted = tmp_path / "data" / "styles" / "default.css"
    planted.parent.mkdir(parents=True)
    planted.write_text("broken", encoding="utf-8")
    assert style_store.load("default") == "/* default */"
