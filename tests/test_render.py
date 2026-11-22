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
    assert "\nbody { color: red; }\n</style>" in page
    # Images are kept within the page whatever the theme says.
    assert "img { max-width: 100%; height: auto; }" in page
    assert "<p>hello</p>" in page
    assert "<script" not in page


def test_render_page_returns_code_block_text(
    renderer: MarkdownRenderer,
) -> None:
    rendered = renderer.render_page("```\nls -la\n```", "")
    assert rendered.code_blocks == ["ls -la"]
    assert 'href="plainpad-copy:0"' in rendered.html


def test_task_list_items_become_disabled_checkboxes(
    renderer: MarkdownRenderer,
) -> None:
    html = renderer.body_html("- [ ] open\n- [x] done")
    assert '<input type="checkbox" disabled/> open' in html
    assert '<input type="checkbox" disabled checked/> done' in html


def test_double_tilde_strikes_but_single_tilde_stays(
    renderer: MarkdownRenderer,
) -> None:
    html = renderer.body_html("~~gone~~ and ~kept~")
    assert "<del>gone</del>" in html
    assert "~kept~" in html


def test_bare_web_address_becomes_link(renderer: MarkdownRenderer) -> None:
    html = renderer.body_html("see https://example.com/page now")
    assert '<a href="https://example.com/page">' in html


def test_footnote_links_to_note_at_bottom(
    renderer: MarkdownRenderer,
) -> None:
    html = renderer.body_html("Claim[^1]\n\n[^1]: Source.")
    assert 'href="#fn:1"' in html
    assert 'id="fn:1"' in html
    # A reused renderer must not carry the footnote into the next note.
    assert "Source." not in renderer.body_html("Plain")


def test_list_nests_at_two_spaces(renderer: MarkdownRenderer) -> None:
    html = renderer.body_html("- top\n  - middle\n    - bottom")
    assert html.count("<ul>") == 3


def test_text_indented_four_spaces_is_not_code(
    renderer: MarkdownRenderer,
) -> None:
    html = renderer.body_html("Intro\n\n    indented words")
    assert "<code>" not in html
    assert "<p>indented words</p>" in html
