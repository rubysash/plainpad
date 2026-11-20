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
    THEMES_DIR,
)
from plainpad.desktop_launch import DesktopLauncher
from plainpad.gui.main_window import MainWindow
from plainpad.library import Library
from plainpad.theme_store import ThemeStore


def main() -> int:
    """Start Plainpad and return the process exit code."""
    application = QApplication(sys.argv)
    # QSettings reads these to decide where the session is remembered.
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setApplicationName(APP_NAME)

    window = MainWindow(
        Library(DATA_DIR), ThemeStore(THEMES_DIR), DesktopLauncher()
    )
    window.show()
    exit_code = application.exec()
    # WebEngine crashes if a page outlives its profile, which goes away
    # with the application, so the window and its View tab go first.
    del window
    return exit_code
