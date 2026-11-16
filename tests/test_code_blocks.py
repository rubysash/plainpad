"""Tests for plainpad.code_blocks."""

import markdown

from plainpad.code_blocks import add_copy_links
from plainpad.config import MARKDOWN_EXTENSIONS


def render(text: str) -> str:
    """Render markdown the way the app does."""
    return markdown.markdown(text, extensions=list(MARKDOWN_EXTENSIONS))


def test_fenced_block_gets_copy_link_and_text() -> None:
    html, texts = add_copy_links(render("```bash\nqm list\n```"))
    assert texts == ["qm list"]
    assert '<a class="copy-code" href="plainpad-copy:0">copy</a>' in html
    assert '<pre><code class="language-bash">qm list' in html


def test_text_is_unescaped() -> None:
    _, texts = add_copy_links(render('```\nif a < b && c > "d":\n```'))
    assert texts == ['if a < b && c > "d":']


def test_multiline_block_keeps_inner_newlines() -> None:
    _, texts = add_copy_links(render("```\none\n\ntwo\n```"))
    assert texts == ["one\n\ntwo"]


def test_blocks_are_numbered_in_page_order() -> None:
    source = "```\nfirst\n```\n\ntext\n\n    indented second\n"
    html, texts = add_copy_links(render(source))
    assert texts == ["first", "indented second"]
    assert html.index("plainpad-copy:0") < html.index("plainpad-copy:1")


def test_inline_code_and_plain_text_are_untouched() -> None:
    source = "Run `ls` now."
    html, texts = add_copy_links(render(source))
    assert texts == []
    assert html == render(source)
