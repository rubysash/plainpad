"""Copy links for the code blocks in rendered HTML.

The View tab runs no JavaScript, so a copy button cannot copy anything by
itself. Instead each code block gets a plain link naming its position, and
the original text of every block is returned alongside the HTML. The GUI
catches a click on the link and copies the matching text.
"""

import html
import re

from plainpad.config import CODE_BLOCK_TEMPLATE, COPY_LINK_SCHEME

# How a code block comes out of Python-Markdown. With syntax
# highlighting on, Pygments adds an empty span before <code>.
CODE_BLOCK_PATTERN = re.compile(
    r"<pre>(?:<span></span>)?<code(?:\s[^>]*)?>(.*?)</code></pre>",
    re.DOTALL,
)
# Highlighting wraps each token in a span. The code's own < and > are
# escaped, so anything that looks like a tag is markup.
TAG_PATTERN = re.compile(r"<[^>]+>")


def add_copy_links(body_html: str) -> tuple[str, list[str]]:
    """Wrap each code block with a copy link.

    Returns the new HTML and the plain text of each block, in page order,
    so link N copies the Nth text. The text loses its highlighting tags,
    is unescaped (``&lt;`` back to ``<``), and loses the trailing newline
    markdown adds.
    """
    texts: list[str] = []

    def wrap(match: re.Match[str]) -> str:
        code = TAG_PATTERN.sub("", match.group(1))
        texts.append(html.unescape(code).rstrip("\n"))
        return CODE_BLOCK_TEMPLATE.format(
            scheme=COPY_LINK_SCHEME,
            index=len(texts) - 1,
            block=match.group(0),
        )

    return CODE_BLOCK_PATTERN.sub(wrap, body_html), texts
