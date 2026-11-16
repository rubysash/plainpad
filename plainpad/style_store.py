"""Persistence for the CSS the user edits in the Settings tab."""

from pathlib import Path

from plainpad.atomic_file import write_text_atomically
from plainpad.config import TEXT_ENCODING


class StyleStore:
    """Loads and saves the preview stylesheet.

    The user's CSS lives in the data folder. Until that file exists, the
    default stylesheet shipped in resources is used.
    """

    def __init__(self, css_file: Path, default_css_file: Path) -> None:
        """Remember where the user's CSS and the shipped default live."""
        self._css_file = css_file
        self._default_css_file = default_css_file

    def load(self) -> str:
        """Return the user's CSS, or the default if none is saved yet."""
        if self._css_file.exists():
            return self._css_file.read_text(encoding=TEXT_ENCODING)
        return self.default_css()

    def save(self, css: str) -> None:
        """Write the user's CSS to disk atomically."""
        write_text_atomically(self._css_file, css)

    def default_css(self) -> str:
        """Return the shipped default stylesheet."""
        return self._default_css_file.read_text(encoding=TEXT_ENCODING)
