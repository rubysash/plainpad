"""Turn formatted clipboard content into markdown for a note.

Programs put HTML on the clipboard when text is copied from them. This
module converts that HTML to markdown and copies its pictures into the
image folder, so a paste from a document or an email keeps its images.
"""

import re
import time
from collections.abc import Callable

from bs4 import BeautifulSoup, Comment
from markdownify import markdownify

from plainpad.config import (
    IMAGE_FETCH_TIMEOUT_S,
    IMAGE_FETCH_TOTAL_S,
    MARKDOWN_BULLETS,
    MARKDOWN_HEADING_STYLE,
    PASTE_DROPPED_TAGS,
)
from plainpad.image_links import image_address_for
from plainpad.image_sources import ImageSourceError, ImageSourceReader
from plainpad.images import ImageFormatError, ImageStore
from plainpad.models import ImportedText

HTML_PARSER = "html.parser"
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
# Google Docs marks bold and italic with styles on spans, not with tags.
_BOLD_STYLE = re.compile(r"font-weight:\s*(bold|[6-9]00)")
_ITALIC_STYLE = re.compile(r"font-style:\s*italic")
# Google Docs wraps a whole copy in a <b> that is styled not to be bold.
_NOT_BOLD_STYLE = re.compile(r"font-weight:\s*(normal|400)")
# A line break in the source leaves a line holding only spaces.
_SPACE_ONLY_LINE = re.compile(r"\n[ \t]+\n")
_BLANK_LINES = re.compile(r"\n{3,}")


def sole_image_address(html: str) -> str | None:
    """Return the image address if the HTML is one picture and no text.

    A browser's "Copy image" describes the picture this way, which is
    how the original file, animation included, can be found.
    """
    soup = BeautifulSoup(html, HTML_PARSER)
    images = soup.find_all("img", src=True)
    if len(images) != 1 or soup.get_text(strip=True):
        return None
    return images[0]["src"]


class RichTextImporter:
    """Converts clipboard HTML to markdown, storing its images."""

    def __init__(
        self,
        images: ImageStore,
        sources: ImageSourceReader,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Remember where images go and how their bytes are fetched.

        ``clock`` returns seconds and is injectable so tests can make
        the download time limit run out.
        """
        self._images = images
        self._sources = sources
        self._clock = clock

    def markdown_from(self, html: str) -> ImportedText:
        """Return the HTML as markdown, with its images stored.

        An image that cannot be fetched or is not an accepted format
        keeps its original address and is counted as missed.
        """
        soup = BeautifulSoup(html, HTML_PARSER)
        self.remove_clutter(soup)
        self.mark_styled_emphasis(soup)
        missed = self.store_images(soup)
        text = markdownify(
            str(soup),
            heading_style=MARKDOWN_HEADING_STYLE,
            bullets=MARKDOWN_BULLETS,
            # Documents rarely mark a table's first row as its header,
            # and a markdown table cannot do without one.
            table_infer_header=True,
        )
        text = _SPACE_ONLY_LINE.sub("\n\n", text)
        return ImportedText(_BLANK_LINES.sub("\n\n", text).strip(), missed)

    def remove_clutter(self, soup: BeautifulSoup) -> None:
        """Drop what a note has no use for.

        That is comments (Word hides whole blocks in them), style and
        metadata tags, and Word's empty ``o:p`` paragraph markers.
        """
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()
        for tag in soup.find_all(PASTE_DROPPED_TAGS):
            tag.decompose()
        for tag in soup.find_all("o:p"):
            tag.unwrap()

    def mark_styled_emphasis(self, soup: BeautifulSoup) -> None:
        """Turn bold and italic given by style into real tags.

        Headings are left alone, because a heading is already
        emphasized and markdown bold inside one is noise.
        """
        for wrapper in soup.find_all("b", style=_NOT_BOLD_STYLE):
            wrapper.unwrap()
        for span in soup.find_all("span", style=True):
            if span.find_parent(HEADING_TAGS) or not span.get_text(strip=True):
                continue
            style = span["style"]
            if _ITALIC_STYLE.search(style):
                span.wrap(soup.new_tag("em"))
            if _BOLD_STYLE.search(style):
                span.wrap(soup.new_tag("strong"))

    def store_images(self, soup: BeautifulSoup) -> int:
        """Point each image at a stored copy; return how many failed.

        All downloads of one paste share a time limit, so a slow server
        cannot hold the app for long.
        """
        deadline = self._clock() + IMAGE_FETCH_TOTAL_S
        stored: dict[str, str | None] = {}
        missed = 0
        for image in soup.find_all("img"):
            address = image.get("src")
            if not address:
                image.decompose()
                continue
            if address not in stored:
                stored[address] = self.store(address, deadline)
            if stored[address] is None:
                missed += 1
            else:
                # Size and title attributes are dropped so the markdown
                # stays a bare image link.
                image.attrs = {
                    "src": image_address_for(stored[address]),
                    "alt": image.get("alt", ""),
                }
        return missed

    def store(self, address: str, deadline: float) -> str | None:
        """Copy one image into the store; return its name, or None."""
        remaining = deadline - self._clock()
        if remaining <= 0:
            return None
        try:
            data = self._sources.read(
                address, min(IMAGE_FETCH_TIMEOUT_S, remaining)
            )
            return self._images.add(data)
        except (ImageSourceError, ImageFormatError, OSError):
            return None
