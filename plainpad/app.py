"""Application entry point.

Builds the storage objects and shows the main window, which applies the
saved theme. This is the only module that knows how all three layers are
constructed.
"""

import sys

# WebEngine must be imported before the QApplication is created.
from PyQt6 import QtWebEngineWidgets  # noqa: F401
from PyQt6.QtWidgets import QApplication

from plainpad.config import (
    APP_NAME,
    DATA_DIR,
    ORGANIZATION_NAME,
    STYLES_DIR_NAME,
    THEMES_DIR,
)
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from plainpad.style_store import StyleStore
from plainpad.theme_store import ThemeStore


def main() -> int:
    """Start Plainpad and return the process exit code."""
    application = QApplication(sys.argv)
    # QSettings reads these to decide where the session is remembered.
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setApplicationName(APP_NAME)

    library = Library(DATA_DIR)
    themes = ThemeStore(THEMES_DIR)
    style_store = StyleStore(DATA_DIR / STYLES_DIR_NAME, themes)
    window = MainWindow(library, style_store, themes)
    window.show()
    exit_code = application.exec()
    # WebEngine crashes if a page outlives its profile, which goes away
    # with the application, so the window and its View tab go first.
    del window
    return exit_code
