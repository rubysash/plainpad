"""Tests for plainpad.render and plainpad.style_store."""

from pathlib import Path

import pytest

from plainpad.render import MarkdownRenderer
from plainpad.style_store import StyleStore


@pytest.fixture
def renderer() -> MarkdownRenderer:
    """One shared renderer, as the app uses it."""
    return MarkdownRenderer()


def test_heading_becomes_h1(renderer: MarkdownRenderer) -> None:
    assert "<h1>Title</h1>" in renderer.body_html("# Title")


def test_fenced_code_becomes_pre_and_code(
    renderer: MarkdownRenderer,
) -> None:
    html = renderer.body_html("```\nprint('hi')\n```")
    assert "<pre><code>" in html
    assert "print(&#x27;hi&#x27;)" in html or "print('hi')" in html


def test_pipe_table_becomes_table(renderer: MarkdownRenderer) -> None:
    html = renderer.body_html("| a | b |\n| - | - |\n| 1 | 2 |")
    assert "<table>" in html
    assert "<td>1</td>" in html


def test_renderer_is_reusable(renderer: MarkdownRenderer) -> None:
    renderer.body_html("# One")
    assert "One" not in renderer.body_html("# Two")


def test_page_html_embeds_css_and_declares_utf8(
    renderer: MarkdownRenderer,
) -> None:
    page = renderer.page_html("hello", "body { color: red; }")
    assert '<meta charset="utf-8">' in page
    assert "<style>\nbody { color: red; }\n</style>" in page
    assert "<p>hello</p>" in page
    assert "<script" not in page


@pytest.fixture
def style_store(tmp_path: Path) -> StyleStore:
    """A StyleStore with a shipped default and no user CSS yet."""
    default = tmp_path / "default.css"
    default.write_text("body { color: green; }", encoding="utf-8")
    return StyleStore(tmp_path / "data" / "preview.css", default)


def test_load_returns_default_when_nothing_saved(
    style_store: StyleStore,
) -> None:
    assert style_store.load() == "body { color: green; }"


def test_save_then_load_returns_saved_css(style_store: StyleStore) -> None:
    style_store.save("p { margin: 0; }")
    assert style_store.load() == "p { margin: 0; }"
    assert style_store.default_css() == "body { color: green; }"
