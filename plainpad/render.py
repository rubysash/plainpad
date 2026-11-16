"""Turn markdown text and a stylesheet into a complete HTML page."""

import markdown

from plainpad.config import MARKDOWN_EXTENSIONS, PREVIEW_PAGE_TEMPLATE


class MarkdownRenderer:
    """Converts markdown to an HTML document for the View tab.

    One instance is reused for every render so the markdown parser and its
    extensions are only set up once.
    """

    def __init__(self) -> None:
        """Create the markdown parser with config.MARKDOWN_EXTENSIONS."""
        self._markdown = markdown.Markdown(
            extensions=list(MARKDOWN_EXTENSIONS)
        )

    def body_html(self, markdown_text: str) -> str:
        """Return the HTML fragment for the markdown, without a page."""
        # reset() clears state left over from the previous document.
        return self._markdown.reset().convert(markdown_text)

    def page_html(self, markdown_text: str, css: str) -> str:
        """Return a full HTML document with the CSS in a style element.

        The page declares UTF-8 and contains no scripts.
        """
        return PREVIEW_PAGE_TEMPLATE.format(
            css=css, body=self.body_html(markdown_text)
        )
