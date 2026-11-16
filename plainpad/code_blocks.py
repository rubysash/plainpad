"""Copy links for the code blocks in rendered HTML.

The View tab runs no JavaScript, so a copy button cannot copy anything by
itself. Instead each code block gets a plain link naming its position, and
the original text of every block is returned alongside the HTML. The GUI
catches a click on the link and copies the matching text.
"""

import html
import re

from plainpad.config import CODE_BLOCK_TEMPLATE, COPY_LINK_SCHEME

# Python-Markdown writes every code block, fenced or indented, this way.
CODE_BLOCK_PATTERN = re.compile(
    r"<pre><code(?:\s[^>]*)?>(.*?)</code></pre>", re.DOTALL
)


def add_copy_links(body_html: str) -> tuple[str, list[str]]:
    """Wrap each code block with a copy link.

    Returns the new HTML and the plain text of each block, in page order,
    so link N copies the Nth text. The text is unescaped (``&lt;`` back to
    ``<``) and loses the trailing newline markdown adds.
    """
    texts: list[str] = []

    def wrap(match: re.Match[str]) -> str:
        texts.append(html.unescape(match.group(1)).rstrip("\n"))
        return CODE_BLOCK_TEMPLATE.format(
            scheme=COPY_LINK_SCHEME,
            index=len(texts) - 1,
            block=match.group(0),
        )

    return CODE_BLOCK_PATTERN.sub(wrap, body_html), texts
