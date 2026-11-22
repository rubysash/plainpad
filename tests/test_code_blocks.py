"""Tests for plainpad.code_blocks."""

from plainpad.code_blocks import add_copy_links
from plainpad.render import MarkdownRenderer


def render(text: str) -> str:
    """Render markdown the way the app does, highlighting included."""
    return MarkdownRenderer().body_html(text)


def test_fenced_block_gets_copy_link_and_text() -> None:
    html, texts = add_copy_links(render("```bash\nqm list\n```"))
    assert texts == ["qm list"]
    assert '<a class="copy-code" href="plainpad-copy:0">copy</a>' in html


def test_text_is_unescaped() -> None:
    _, texts = add_copy_links(render('```\nif a < b && c > "d":\n```'))
    assert texts == ['if a < b && c > "d":']


def test_highlighted_text_is_copied_without_its_tags() -> None:
    source = '```python\nif a < b:\n    print("<p>")\n```'
    html, texts = add_copy_links(render(source))
    assert '<span class="k">if</span>' in html
    assert texts == ['if a < b:\n    print("<p>")']


def test_multiline_block_keeps_inner_newlines() -> None:
    _, texts = add_copy_links(render("```\none\n\ntwo\n```"))
    assert texts == ["one\n\ntwo"]


def test_blocks_are_numbered_in_page_order() -> None:
    source = "```\nfirst\n```\n\ntext\n\n```python\nsecond\n```\n"
    html, texts = add_copy_links(render(source))
    assert texts == ["first", "second"]
    assert html.index("plainpad-copy:0") < html.index("plainpad-copy:1")


def test_inline_code_and_plain_text_are_untouched() -> None:
    source = "Run `ls` now."
    html, texts = add_copy_links(render(source))
    assert texts == []
    assert html == render(source)
