"""Persistence for the CSS the user edits in the Settings tab.

Each theme has its own user CSS, so switching themes never mixes one
theme's View tab style into another. The Default theme cannot be edited:
it always uses its shipped CSS, so it stays a safe fallback.
"""

from pathlib import Path

from plainpad.atomic_file import write_text_atomically
from plainpad.config import DEFAULT_THEME, STYLE_FILE_EXTENSION, TEXT_ENCODING
from plainpad.theme_store import ThemeStore


class StyleStore:
    """Loads and saves the View tab stylesheet for each theme.

    Until the user saves CSS for a theme, the theme's shipped CSS is used.
    """

    def __init__(self, styles_dir: Path, themes: ThemeStore) -> None:
        """Remember where user CSS lives and where shipped CSS comes from."""
        self._styles_dir = styles_dir
        self._themes = themes

    def load(self, theme: str) -> str:
        """Return the user's CSS for a theme, or its shipped CSS."""
        path = self.path_of(theme)
        if self.is_editable(theme) and path.exists():
            return path.read_text(encoding=TEXT_ENCODING)
        return self.default_css(theme)

    def save(self, theme: str, css: str) -> None:
        """Write the user's CSS for a theme atomically.

        Raises ValueError for the Default theme, which is read-only.
        """
        if not self.is_editable(theme):
            raise ValueError(f"The {theme} theme cannot be edited.")
        write_text_atomically(self.path_of(theme), css)

    def default_css(self, theme: str) -> str:
        """Return the CSS a theme ships with."""
        return self._themes.preview_css(theme)

    @staticmethod
    def is_editable(theme: str) -> bool:
        """Return True unless the theme is the read-only Default."""
        return theme != DEFAULT_THEME

    def path_of(self, theme: str) -> Path:
        """Return the file holding the user's CSS for a theme."""
        return self._styles_dir / f"{theme}{STYLE_FILE_EXTENSION}"
