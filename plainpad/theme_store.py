"""The themes shipped with the app, one folder each.

A theme folder holds ``app.qss`` (the window chrome), ``preview.css`` (the
View tab), and optionally ``theme.json`` with the label for the menu. Any
folder with both stylesheets is a theme, so adding one needs no code.
"""

import json
from pathlib import Path

from plainpad.config import (
    DEFAULT_THEME,
    TEXT_ENCODING,
    THEME_INFO_FILE_NAME,
    THEME_PREVIEW_CSS_FILE_NAME,
    THEME_QSS_FILE_NAME,
)
from plainpad.models import Theme


class ThemeStore:
    """Finds themes and reads their stylesheets."""

    def __init__(self, themes_dir: Path) -> None:
        """Remember the folder that holds one subfolder per theme."""
        self._themes_dir = themes_dir

    def themes(self) -> list[Theme]:
        """Return every complete theme, Default first, then by label."""
        found = [
            Theme(folder.name, self.label_of(folder))
            for folder in self._themes_dir.iterdir()
            if self.is_complete(folder)
        ]
        found.sort(
            key=lambda t: (t.name != DEFAULT_THEME, t.label.casefold())
        )
        return found

    def resolve(self, name: str | None) -> str:
        """Return ``name`` if it is a complete theme, else Default."""
        if name and self.is_complete(self._themes_dir / name):
            return name
        return DEFAULT_THEME

    def qss(self, name: str) -> str:
        """Return a theme's window stylesheet."""
        return self.read(name, THEME_QSS_FILE_NAME)

    def preview_css(self, name: str) -> str:
        """Return a theme's shipped View tab stylesheet."""
        return self.read(name, THEME_PREVIEW_CSS_FILE_NAME)

    def read(self, name: str, file_name: str) -> str:
        """Return one file of a theme as text."""
        path = self._themes_dir / self.resolve(name) / file_name
        return path.read_text(encoding=TEXT_ENCODING)

    @staticmethod
    def is_complete(folder: Path) -> bool:
        """Return True if a folder has both stylesheets a theme needs."""
        return (folder / THEME_QSS_FILE_NAME).is_file() and (
            folder / THEME_PREVIEW_CSS_FILE_NAME
        ).is_file()

    @staticmethod
    def label_of(folder: Path) -> str:
        """Return the menu label from theme.json, or the folder name."""
        try:
            info = json.loads(
                (folder / THEME_INFO_FILE_NAME).read_text(
                    encoding=TEXT_ENCODING
                )
            )
            return str(info["label"])
        except (OSError, ValueError, KeyError, TypeError):
            return folder.name.title()
