"""Tests for plainpad.render."""

import pytest

from plainpad.render import MarkdownRenderer


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


def test_render_page_embeds_css_and_declares_utf8(
    renderer: MarkdownRenderer,
) -> None:
    page = renderer.render_page("hello", "body { color: red; }").html
    assert '<meta charset="utf-8">' in page
    assert "<style>\nbody { color: red; }\n</style>" in page
    assert "<p>hello</p>" in page
    assert "<script" not in page


def test_render_page_returns_code_block_text(
    renderer: MarkdownRenderer,
) -> None:
    rendered = renderer.render_page("```\nls -la\n```", "")
    assert rendered.code_blocks == ["ls -la"]
    assert 'href="plainpad-copy:0"' in rendered.html
