"""Turn a note into formatted text that other programs can paste.

A note's pictures are local files, which a browser or mail program cannot
read. Here they are packed into the HTML itself as ``data:`` addresses, so
the formatted text carries its images with it.
"""

import base64
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from bs4 import BeautifulSoup, Comment

from plainpad.config import (
    COPY_LINK_SCHEME,
    IMAGE_MIME_TYPES,
    PASTE_DROPPED_TAGS,
)
from plainpad.image_links import stored_image_name
from plainpad.image_sources import FILE_SCHEME
from plainpad.images import ImageStore
from plainpad.render import MarkdownRenderer

HTML_PARSER = "html.parser"
# Wrappers the clipboard puts around a copied fragment. Left in, they
# would be nested inside the ones added when the copy is put back.
FRAGMENT_WRAPPER_TAGS = ("html", "body")
# Attributes through which the View tab's theme rides along on a copy.
THEME_ATTRIBUTES = ("style", "class")


class RichTextExporter:
    """Builds clipboard HTML with every stored image embedded."""

    def __init__(self, renderer: MarkdownRenderer, images: ImageStore) -> None:
        """Remember the markdown renderer and where the images are."""
        self._renderer = renderer
        self._images = images

    def note_html(self, markdown_text: str) -> str:
        """Return a whole note as HTML with its images embedded.

        No theme CSS is applied, so the receiving program uses its own
        fonts and colors.
        """
        soup = BeautifulSoup(
            self._renderer.body_html(markdown_text), HTML_PARSER
        )
        self.embed_images(soup)
        return str(soup)

    def selection_html(self, copied_html: str) -> str:
        """Return what the View tab copied, made fit for other programs.

        The browser engine writes the theme's colors and fonts into the
        copied HTML and names images by local file. This removes the
        theme, drops code block copy links, and embeds the images.
        """
        soup = BeautifulSoup(copied_html, HTML_PARSER)
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()
        for tag in soup.find_all(FRAGMENT_WRAPPER_TAGS):
            tag.unwrap()
        for tag in soup.find_all(PASTE_DROPPED_TAGS):
            tag.decompose()
        for link in soup.find_all("a", href=True):
            if link["href"].startswith(f"{COPY_LINK_SCHEME}:"):
                link.decompose()
        for tag in soup.find_all(True):
            for attribute in THEME_ATTRIBUTES:
                del tag[attribute]
        self.embed_images(soup)
        return str(soup).strip()

    def embed_images(self, soup: BeautifulSoup) -> None:
        """Replace each stored image's address with its content.

        Images on the web keep their address, since the receiving
        program can fetch those itself.
        """
        for image in soup.find_all("img", src=True):
            name = self.stored_name(image["src"])
            if name is None or not self._images.exists(name):
                continue
            mime_type = IMAGE_MIME_TYPES.get(Path(name).suffix.lower())
            if mime_type is None:
                continue
            encoded = base64.b64encode(self._images.read(name)).decode()
            image["src"] = f"data:{mime_type};base64,{encoded}"

    def stored_name(self, address: str) -> str | None:
        """Return the stored image an address refers to, if any.

        A note links images relatively; the browser engine turns that
        into a ``file:`` address inside the images folder. Both count.
        """
        name = stored_image_name(address)
        if name is not None:
            return name
        parts = urlsplit(address)
        if parts.scheme.lower() != FILE_SCHEME:
            return None
        path = Path(url2pathname(parts.path))
        inside = path.parent.resolve() == self._images.folder.resolve()
        return path.name if inside else None
